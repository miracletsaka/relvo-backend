from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse, urldefrag

import httpx
import tldextract
from bs4 import BeautifulSoup
from readability import Document


# ── Constants ─────────────────────────────────────────────────────────────────

MAX_PAGES          = 12       # hard cap on pages fetched per scrape
MAX_CHARS_PER_PAGE = 8_000    # trim each page's text to avoid huge payloads
MAX_TOTAL_CHARS    = 60_000   # final cap on combined raw_text
REQUEST_TIMEOUT    = 12.0     # seconds per request

# Pages whose paths contain these strings are high-value
PRIORITY_KEYWORDS = [
    "about", "service", "product", "pricing", "price", "plan",
    "solution", "feature", "team", "work", "case", "client",
    "faq", "contact", "blog", "news",
]

# Boilerplate line fingerprints — exact lines found on almost every page
# (nav items, cookie banners, footer text). Built dynamically during scrape.
_BOILERPLATE_THRESHOLD = 3   # if a line appears on ≥ this many pages → boilerplate


CSS_VAR_COLOR_RE = re.compile(
    r"--[\w-]*(?:color|colour|bg|background|accent|primary|secondary)[\w-]*\s*:\s*(#[0-9a-fA-F]{3,8})\b",
    re.IGNORECASE,
)
SCHEMA_TYPE_RE = re.compile(r'"@type"\s*:\s*"([^"]+)"')


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class PageData:
    url:         str
    title:       str
    description: str
    text:        str
    og_tags:     dict[str, str]
    schema_types: list[str]
    colors:      list[str]
    word_count:  int


@dataclass
class ScrapeResult:
    pages:          list[str]          # URLs actually fetched
    raw_text:       str                # deduplicated combined text
    colors:         list[str]          # brand colors (CSS vars + theme-color)
    page_data:      list[PageData]     # per-page structured data
    meta: dict = field(default_factory=dict)  # og:title, description, schema types


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_url(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return ""
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    # strip trailing slash for consistency
    return u.rstrip("/")


def _same_site(base_url: str, candidate: str) -> bool:
    a = tldextract.extract(base_url)
    b = tldextract.extract(candidate)
    return (a.domain, a.suffix) == (b.domain, b.suffix)


def _url_priority_score(url: str, brand_keywords: list[str]) -> int:
    """
    Higher = more relevant to scrape first.
    Brand-specific keywords beat generic priority words.
    """
    path = urlparse(url).path.lower()
    score = 0
    for kw in brand_keywords:
        if kw in path:
            score += 10          # brand-specific match is highest value
    for kw in PRIORITY_KEYWORDS:
        if kw in path:
            score += 3
    # penalise very deep paths (likely blog posts, not key pages)
    depth = path.count("/")
    score -= max(0, depth - 2)
    return score


def _line_fingerprint(line: str) -> str:
    """Stable hash of a normalised line (for boilerplate detection)."""
    return hashlib.md5(line.strip().lower().encode()).hexdigest()


def _discover_links(html: str, base_url: str) -> list[str]:
    """Extract all same-site internal links from a page."""
    soup  = BeautifulSoup(html, "lxml")
    links = []
    seen  = set()
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        full, _ = urldefrag(urljoin(base_url, href))
        if full in seen:
            continue
        seen.add(full)
        if not _same_site(base_url, full):
            continue
        # skip obvious non-content URLs
        parsed = urlparse(full)
        path   = parsed.path.lower()
        if any(path.endswith(ext) for ext in (
            ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg",
            ".webp", ".mp4", ".zip", ".xml", ".json",
        )):
            continue
        links.append(full)
    return links


def _extract_meta(soup: BeautifulSoup) -> tuple[str, str, dict[str, str], list[str]]:
    """Returns (title, description, og_tags, schema_types)."""
    title = ""
    t = soup.find("title")
    if t:
        title = t.get_text(strip=True)

    description = ""
    m = soup.find("meta", attrs={"name": "description"})
    if m and m.get("content"):
        description = m["content"].strip()

    og_tags: dict[str, str] = {}
    for tag in soup.find_all("meta", property=re.compile(r"^og:")):
        key = tag.get("property", "").replace("og:", "")
        val = tag.get("content", "").strip()
        if key and val:
            og_tags[key] = val

    # schema.org JSON-LD
    schema_types: list[str] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            found = SCHEMA_TYPE_RE.findall(json.dumps(data))
            schema_types.extend(found)
        except Exception:
            pass

    return title, description, og_tags, schema_types


def _extract_colors(html: str, soup: BeautifulSoup) -> list[str]:
    """
    Only extract colors from:
    1. CSS custom properties matching color/bg/accent/primary/secondary
    2. meta theme-color
    Avoids the noise of every random hex in raw HTML.
    """
    colors: set[str] = set()

    # CSS custom properties
    for match in CSS_VAR_COLOR_RE.finditer(html):
        colors.add(match.group(1).lower())

    # meta theme-color
    tc = soup.find("meta", attrs={"name": "theme-color"})
    if tc and tc.get("content", "").startswith("#"):
        colors.add(tc["content"].strip().lower())

    return sorted(colors)[:15]


def _extract_clean_text(html: str) -> str:
    """
    Use readability for main content extraction, then aggressively strip
    short/navigation lines that readability sometimes leaves behind.
    """
    try:
        doc          = Document(html)
        cleaned_html = doc.summary(html_partial=True)
    except Exception:
        cleaned_html = html

    soup  = BeautifulSoup(cleaned_html, "lxml")
    lines = soup.get_text("\n", strip=True).splitlines()

    # Drop lines that are very short (nav items, button labels)
    # or look like UI chrome
    meaningful = []
    for line in lines:
        line = line.strip()
        if len(line) < 20:          # too short to be real content
            continue
        if line.count("|") > 3:     # nav separator line
            continue
        if line.count("·") > 3:
            continue
        meaningful.append(line)

    text = "\n".join(meaningful)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:MAX_CHARS_PER_PAGE]


def _deduplicate_across_pages(pages_text: list[tuple[str, str]]) -> str:
    """
    Combine text from multiple pages while removing boilerplate lines
    (lines that appear on 3+ pages are assumed to be nav/footer noise).

    pages_text: list of (url, text) tuples
    """
    # Count how often each line fingerprint appears
    line_counts: dict[str, int] = {}
    for _, text in pages_text:
        seen_in_page: set[str] = set()
        for line in text.splitlines():
            fp = _line_fingerprint(line)
            if fp not in seen_in_page:
                line_counts[fp] = line_counts.get(fp, 0) + 1
                seen_in_page.add(fp)

    # Keep only lines that are NOT boilerplate
    sections: list[str] = []
    for url, text in pages_text:
        unique_lines = []
        for line in text.splitlines():
            fp = _line_fingerprint(line)
            if line_counts.get(fp, 0) < _BOILERPLATE_THRESHOLD:
                unique_lines.append(line)

        section = "\n".join(unique_lines).strip()
        if section:
            sections.append(f"── {url} ──\n{section}")

    combined = "\n\n".join(sections)
    return combined[:MAX_TOTAL_CHARS]


# ── Main scraper ──────────────────────────────────────────────────────────────

async def scrape_brand_site(
    website_url: str,
    brand_keywords: Optional[list[str]] = None,
    timeout_s: float = REQUEST_TIMEOUT,
    max_pages: int = MAX_PAGES,
) -> ScrapeResult:
    """
    Advanced brand site scraper.

    Args:
        website_url:    The brand's website (e.g. "https://neuroflow.ai/whatsapp")
        brand_keywords: Keywords specific to this brand to prioritise relevant pages
                        (e.g. ["whatsapp", "chatbot", "automation"] for WhatsApp brand).
                        Pulled from brand.name / brand.slug if not provided.
        timeout_s:      Per-request timeout in seconds.
        max_pages:      Maximum pages to fetch (default 12).
    """
    base = _normalize_url(website_url)
    if not base:
        raise ValueError("website_url is empty")

    kws = [kw.lower() for kw in (brand_keywords or [])]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; NeuroflowBot/2.0; "
            "+https://neuroflow.ai/bot)"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    fetched_urls:  list[str]      = []
    page_data_list: list[PageData] = []
    all_colors:    set[str]       = set()
    pages_text:    list[tuple[str, str]] = []

    # ── Phase 1: fetch homepage + discover all internal links ─────────────────
    discovered: list[str] = []
    homepage_html = ""

    async with httpx.AsyncClient(
        timeout=timeout_s,
        follow_redirects=True,
        headers=headers,
    ) as client:

        # Always start with the given URL (could be a sub-page like /whatsapp)
        try:
            r = await client.get(base)
            if _same_site(base, str(r.url)):
                homepage_html = r.text or ""
                discovered    = _discover_links(homepage_html, base)
                fetched_urls.append(str(r.url))
        except Exception as e:
            raise ValueError(f"Failed to fetch {base}: {e}")

        # ── Phase 2: score + rank discovered links ────────────────────────────
        # Filter to same-site, score by brand keywords + priority words
        candidates = [
            (url, _url_priority_score(url, kws))
            for url in discovered
            if _same_site(base, url) and url not in fetched_urls
        ]
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Take top N after homepage
        pages_to_fetch = [url for url, _ in candidates[:max_pages - 1]]

        # ── Phase 3: fetch each page concurrently (batches of 4) ─────────────
        async def fetch_one(url: str) -> tuple[str, str] | None:
            """Returns (final_url, html) or None on failure."""
            try:
                resp = await client.get(url)
                final = str(resp.url)
                if not _same_site(base, final):
                    return None
                return final, resp.text or ""
            except Exception:
                return None

        batch_size = 4
        raw_pages: list[tuple[str, str]] = [
            (fetched_urls[0], homepage_html)  # include homepage
        ]

        for i in range(0, len(pages_to_fetch), batch_size):
            batch   = pages_to_fetch[i: i + batch_size]
            results = await asyncio.gather(*[fetch_one(u) for u in batch])
            for res in results:
                if res is not None:
                    final_url, html = res
                    if final_url not in [u for u, _ in raw_pages]:
                        raw_pages.append((final_url, html))

    # ── Phase 4: parse each page ──────────────────────────────────────────────
    for page_url, html in raw_pages:
        if not html.strip():
            continue

        soup = BeautifulSoup(html, "lxml")

        title, description, og_tags, schema_types = _extract_meta(soup)
        page_colors = _extract_colors(html, soup)
        text        = _extract_clean_text(html)
        word_count  = len(text.split())

        for c in page_colors:
            all_colors.add(c)

        if text:
            pages_text.append((page_url, text))

        page_data_list.append(PageData(
            url=page_url,
            title=title,
            description=description,
            text=text,
            og_tags=og_tags,
            schema_types=list(set(schema_types)),
            colors=page_colors,
            word_count=word_count,
        ))

    # Sort pages by word count descending — richest pages first in output
    page_data_list.sort(key=lambda p: p.word_count, reverse=True)
    pages_text_sorted = [(p.url, p.text) for p in page_data_list]

    # ── Phase 5: deduplicate across pages ────────────────────────────────────
    raw_text = _deduplicate_across_pages(pages_text_sorted)

    # ── Phase 6: build top-level meta from homepage / richest page ────────────
    top = page_data_list[0] if page_data_list else None
    meta = {}
    if top:
        meta["title"]        = top.og_tags.get("title") or top.title
        meta["description"]  = top.og_tags.get("description") or top.description
        meta["og_image"]     = top.og_tags.get("image", "")
        meta["schema_types"] = list({
            t for p in page_data_list for t in p.schema_types
        })
        meta["pages_fetched"] = len(page_data_list)
        meta["total_words"]   = sum(p.word_count for p in page_data_list)

    return ScrapeResult(
        pages=[p.url for p in page_data_list],
        raw_text=raw_text,
        colors=sorted(all_colors)[:15],
        page_data=page_data_list,
        meta=meta,
    )


# ── Brand-aware wrapper ───────────────────────────────────────────────────────
# Call this from your FastAPI route instead of scrape_brand_site directly.

async def scrape_brand(
    website_url: str,
    brand_name:  str = "",
    brand_slug:  str = "",
) -> ScrapeResult:
    """
    Wrapper that derives brand_keywords from brand_name + slug automatically.

    Example:
        result = await scrape_brand(
            website_url = "https://neuroflow.ai/whatsapp",
            brand_name  = "NeuroFlow WhatsApp",
            brand_slug  = "neuroflow-whatsapp",
        )
    """
    # Derive keywords from brand name + slug
    name_words = re.split(r"[\s\-_]+", (brand_name or "").lower())
    slug_words = re.split(r"[\s\-_]+", (brand_slug or "").lower())
    keywords   = list({
        w for w in name_words + slug_words
        if len(w) > 2 and w not in ("the", "and", "for", "ltd", "inc")
    })

    return await scrape_brand_site(
        website_url    = website_url,
        brand_keywords = keywords,
    )