import os
import re
import json
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

IMPORTANT_PATH_HINTS = [
    "/about",
    "/about-us",
    "/services",
    "/products",
    "/solutions",
    "/company",
    "/who-we-are",
    "/what-we-do",
]

MAX_PAGES = 5
MAX_TEXT_CHARS = 18000


def normalize_website_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return url
    if not re.match(r"^https?://", url, re.I):
        url = f"https://{url}"
    return url


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def is_same_domain(base_url: str, candidate_url: str) -> bool:
    try:
        return urlparse(base_url).netloc == urlparse(candidate_url).netloc
    except Exception:
        return False


def extract_json_ld(soup: BeautifulSoup) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (tag.string or tag.get_text() or "").strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                out.extend([x for x in parsed if isinstance(x, dict)])
            elif isinstance(parsed, dict):
                out.append(parsed)
        except Exception:
            continue
    return out


def extract_page_content(url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = clean_text(soup.title.get_text()) if soup.title else ""

    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"}
    )
    if meta_tag:
        meta_description = clean_text(meta_tag.get("content", ""))

    headings = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        text = clean_text(h.get_text(" ", strip=True))
        if text and len(text) > 2:
            headings.append(text)

    paragraphs = []
    main = soup.find("main") or soup.body or soup
    for p in main.find_all(["p", "li"]):
        text = clean_text(p.get_text(" ", strip=True))
        if len(text) >= 40:
            paragraphs.append(text)

    links = []
    for a in soup.find_all("a", href=True):
        href = clean_text(a.get("href"))
        text = clean_text(a.get_text(" ", strip=True))
        if not href:
            continue
        full = urljoin(url, href)
        if is_same_domain(url, full):
            links.append({
                "url": full,
                "text": text,
            })

    json_ld = extract_json_ld(soup)

    return {
        "url": url,
        "title": title,
        "meta_description": meta_description,
        "headings": headings[:30],
        "paragraphs": paragraphs[:80],
        "links": links[:200],
        "json_ld": json_ld[:20],
    }


async def fetch_html(client: httpx.AsyncClient, url: str) -> Optional[str]:
    try:
        res = await client.get(url, follow_redirects=True)
        ct = (res.headers.get("content-type") or "").lower()
        if res.status_code >= 400:
            return None
        if "text/html" not in ct:
            return None
        return res.text
    except Exception:
        return None


def choose_priority_links(base_url: str, all_links: list[dict[str, str]]) -> list[str]:
    seen = set()
    chosen = []

    for hint in IMPORTANT_PATH_HINTS:
        for item in all_links:
            u = item.get("url") or ""
            path = urlparse(u).path.lower().rstrip("/")
            if path == hint or path.startswith(hint + "/"):
                if u not in seen:
                    seen.add(u)
                    chosen.append(u)

    if len(chosen) >= MAX_PAGES - 1:
        return chosen[: MAX_PAGES - 1]

    fallback_keywords = ("about", "service", "product", "solution", "company")
    for item in all_links:
        u = item.get("url") or ""
        if u in seen:
            continue
        text = (item.get("text") or "").lower()
        path = urlparse(u).path.lower()
        if any(k in text or k in path for k in fallback_keywords):
            seen.add(u)
            chosen.append(u)
        if len(chosen) >= MAX_PAGES - 1:
            break

    return chosen[: MAX_PAGES - 1]


def compress_scrape_for_prompt(scrape: dict[str, Any]) -> str:
    parts = []

    for page in scrape.get("pages", []):
        parts.append(f"URL: {page.get('url')}")
        if page.get("title"):
            parts.append(f"Title: {page['title']}")
        if page.get("meta_description"):
            parts.append(f"Meta description: {page['meta_description']}")
        if page.get("headings"):
            parts.append("Headings:")
            parts.extend([f"- {h}" for h in page["headings"][:12]])
        if page.get("paragraphs"):
            parts.append("Key text:")
            parts.extend([f"- {p}" for p in page["paragraphs"][:18]])

        if page.get("json_ld"):
            business_objects = []
            for obj in page["json_ld"][:8]:
                t = obj.get("@type")
                name = obj.get("name")
                desc = obj.get("description")
                if t or name or desc:
                    business_objects.append({
                        "@type": t,
                        "name": name,
                        "description": desc,
                    })
            if business_objects:
                parts.append("Structured data:")
                parts.append(json.dumps(business_objects, ensure_ascii=False))

        parts.append("")

    text = "\n".join(parts)
    return text[:MAX_TEXT_CHARS]


async def advanced_scrape_website(url: str) -> dict[str, Any]:
    normalized = normalize_website_url(url)
    if not normalized:
        return {"website": "", "pages": [], "combined_text": ""}

    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(headers=headers, timeout=20.0) as client:
        homepage_html = await fetch_html(client, normalized)
        if not homepage_html:
            return {"website": normalized, "pages": [], "combined_text": ""}

        homepage = extract_page_content(normalized, homepage_html)
        pages = [homepage]

        priority_links = choose_priority_links(normalized, homepage.get("links", []))

        for link in priority_links:
            html = await fetch_html(client, link)
            if not html:
                continue
            try:
                pages.append(extract_page_content(link, html))
            except Exception:
                continue

    combined = compress_scrape_for_prompt({
        "website": normalized,
        "pages": pages,
    })

    return {
        "website": normalized,
        "pages": pages,
        "combined_text": combined,
    }


async def enrich_business_profile_with_gpt(
    *,
    org_name: str,
    website: Optional[str],
    tagline: Optional[str],
    description: Optional[str],
    business_type: Optional[str],
    company_size: Optional[str],
    founded_year: Optional[int],
) -> dict[str, Any]:
    scraped = await advanced_scrape_website(website or "")

    original_description = clean_text(description or "")
    original_tagline = clean_text(tagline or "")
    scraped_text = scraped.get("combined_text", "")

    # fallback if OpenAI not configured
    if not OpenAI or not os.getenv("OPENAI_API_KEY"):
        return {
            "description": original_description,
            "tagline": original_tagline,
            "summary": original_description[:240] if original_description else "",
            "detected_business_focus": business_type,
            "scraped_website": scraped.get("website"),
            "scrape_preview": scraped_text[:2500],
        }

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""
You are helping enrich a business profile during onboarding.

Your task:
- Read the user's own business description and tagline.
- Read the scraped website content.
- Produce a stronger, clearer, more accurate business description.
- Keep it factual and grounded in the website.
- Do not invent services that are not supported.
- Prefer concise, premium SaaS/business language.
- Description should be 80-180 words.
- Tagline should be short and polished.
- Return strict JSON only.

Input:
org_name: {org_name or ""}
website: {website or ""}
user_tagline: {original_tagline}
user_description: {original_description}
business_type: {business_type or ""}
company_size: {company_size or ""}
founded_year: {founded_year or ""}

Scraped website content:
{scraped_text[:14000]}

Return JSON:
{{
  "description": "...",
  "tagline": "...",
  "summary": "...",
  "detected_business_focus": "...",
  "confidence": "high|medium|low"
}}
""".strip()

    try:
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": "You rewrite business profiles accurately and return JSON only.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        raw = (resp.choices[0].message.content or "").strip()
        data = json.loads(raw)

        return {
            "description": clean_text(data.get("description") or original_description),
            "tagline": clean_text(data.get("tagline") or original_tagline),
            "summary": clean_text(data.get("summary") or ""),
            "detected_business_focus": clean_text(data.get("detected_business_focus") or business_type or ""),
            "confidence": clean_text(data.get("confidence") or "medium"),
            "scraped_website": scraped.get("website"),
            "scrape_preview": scraped_text[:2500],
        }
    except Exception:
        return {
            "description": original_description,
            "tagline": original_tagline,
            "summary": original_description[:240] if original_description else "",
            "detected_business_focus": business_type,
            "confidence": "low",
            "scraped_website": scraped.get("website"),
            "scrape_preview": scraped_text[:2500],
        }