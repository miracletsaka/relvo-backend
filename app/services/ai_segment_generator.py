"""
backend/app/services/ai_segment_generator.py

FIXED:
- TYPE_ALIAS: "hero" → "hero_text" (was "hero_image" which has no SEGMENT_FIELDS entry)
- SEGMENT_FIELDS: added "hero_text" key (removed "hero_image" alias that broke lookups)
- _fields_for_generation: checks "hero_text" not "hero_image"
- hero_media: now calls LLM with a rich prompt instead of returning blueprint directly
- validate_media_segment: enforces exactly 1 image shape, adds background if missing
- similarity threshold: raised to 0.80 so creative layouts aren't rejected
- build_hero_media_prompt: new function — AI-composed cinematic media layouts
- Expanded composition vocabulary arrays for more visual variety
- Added glass / glow / layered bg language to all prompts
"""

import json
import logging
import os
import random
import re
import string
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.services.blueprints import get_blueprint

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

PAD = 56
CANVAS_WIDTH_DEFAULT = 1080


# ─────────────────────────────────────────────────────────────────────────────
# Type maps
# ─────────────────────────────────────────────────────────────────────────────

TYPE_ALIAS: Dict[str, str] = {
    # Hero text variants — all resolve to "hero_text"
    "hero":            "hero_text",
    "hello":           "hero_text",
    "hero_text":       "hero_text",
    "hero_image":      "hero_text",   # legacy alias kept so old callers don't break

    # Hero media variants
    "hero_media":        "hero_media",
    "hero_image_layer":  "hero_media",
    "hello_image":       "hero_media",

    # Content segments
    "offer":        "offer_block",
    "price":        "price_block",
    "features":     "feature_list",
    "review":       "review_block",
    "sponsor":      "sponsor_bar",
    "cta":          "cta_button",
    "footer":       "footer",
    "headline":     "headline",
    "product_card": "product_card",
}

# What gets returned to the frontend in segment_type
PUBLIC_TYPE: Dict[str, str] = {
    "hero_text":    "hero",
    "hero_media":   "hero_media",
    "offer_block":  "offer",
    "price_block":  "price",
    "feature_list": "features",
    "review_block": "review",
    "sponsor_bar":  "sponsor",
    "cta_button":   "cta",
    "footer":       "footer",
    "headline":     "headline",
    "product_card": "product_card",
}


# ─────────────────────────────────────────────────────────────────────────────
# Segment field definitions
# ─────────────────────────────────────────────────────────────────────────────

SEGMENT_FIELDS: Dict[str, List[str]] = {
    # hero_text is the canonical internal name for the text/copy layer
    "hero_text": ["hook", "subheading"],

    # hero_media has no text fields — it is pure visual layer
    "hero_media": [],

    "offer_block": [
        "offer_title",
        "offer_description",
        "discount_label",
        "price",
        "compare_at_price",
    ],
    "price_block":  ["price", "compare_at_price", "discount_label"],
    "feature_list": ["headline", "feature_1", "feature_2", "feature_3", "feature_4"],
    "review_block": ["review_text", "review_author", "review_rating"],
    "sponsor_bar":  ["proof"],
    "cta_button":   ["cta_text", "proof"],
    "footer":       ["contact_row1", "contact_row2", "business_website"],
    "headline":     ["hook", "subheading", "proof"],
    "product_card": [
        "offer_title",
        "offer_description",
        "price",
        "compare_at_price",
        "discount_label",
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# Typography / sizing constraints
# ─────────────────────────────────────────────────────────────────────────────

MIN_FONT: Dict[str, int] = {
    "hook":             72,
    "headline":         64,
    "subheading":       28,
    "cta_text":         26,
    "proof":            22,
    "offer_title":      52,
    "offer_description":24,
    "price":            60,
    "compare_at_price": 24,
    "discount_label":   22,
    "feature_1":        24,
    "feature_2":        24,
    "feature_3":        24,
    "feature_4":        24,
    "review_text":      26,
    "review_author":    22,
    "review_rating":    22,
    "business_website": 18,
    "contact_row1":     18,
    "contact_row2":     16,
}

MIN_BOX: Dict[str, tuple[int, int]] = {
    "hook":             (520, 150),
    "headline":         (520, 110),
    "subheading":       (420, 70),
    "cta_text":         (240, 56),
    "proof":            (320, 48),
    "offer_title":      (480, 100),
    "offer_description":(420, 70),
    "price":            (300, 90),
    "compare_at_price": (220, 48),
    "discount_label":   (240, 44),
    "feature_1":        (320, 46),
    "feature_2":        (320, 46),
    "feature_3":        (320, 46),
    "feature_4":        (320, 46),
    "review_text":      (480, 92),
    "review_author":    (260, 42),
    "review_rating":    (140, 32),
    "business_website": (260, 28),
    "contact_row1":     (420, 30),
    "contact_row2":     (420, 26),
}


# ─────────────────────────────────────────────────────────────────────────────
# Expanded creative vocabulary — richer for commercial output
# ─────────────────────────────────────────────────────────────────────────────

_LAYOUT_STRUCTURES = [
    "pure poster typography with strong safe margins",
    "large left headline with supporting line anchored below",
    "centered headline with strong dark negative space",
    "split dark panel composition using typography and accent geometry only",
    "diagonal visual flow created with rules and accent shapes",
    "top-heavy headline with small proof line at the bottom",
    "bottom-anchored headline with large empty space above",
    "editorial grid layout with text blocks aligned to columns",
    "bold stacked typography layout with accent underline",
    "minimal Swiss grid composition with strong spacing",
    "large headline cropped slightly by canvas edge for editorial energy",
    "right-aligned headline system with left accent stripe",
    "center-weighted headline with subtle geometric background",
    "asymmetric typography composition with one strong focal point",
    "dark premium card layout with text-only hierarchy",
    "glass-card panel floating over dark gradient background",
    "layered frosted panel with glow orb behind the text block",
    "dramatic single-word hook at 200px with thin subtext below",
    "luxury two-column text split with vertical rule divider",
    "cinematic bottom-third layout with gradient fade up",
]

_TEXT_HIERARCHIES = [
    "hook is dominant at around 90px, subheading small below",
    "hook fills the width in two stacked lines",
    "hook top-left, subheading bottom-right for diagonal tension",
    "hook is enormous and cropped slightly by the canvas edge",
    "subheading first as an eyebrow label, hook large below it",
    "three text elements stacked with generous gap between each",
    "hook and subheading share the same baseline at different sizes",
    "hook centred, subheading left-aligned below",
    "hook right-aligned large, subheading left-aligned for contrast",
    "hook at top, proof or subheading at very bottom",
    "all text right-aligned with consistent margin",
    "hook bottom-left, subheading mid-right with premium scattered flow",
    "eyebrow label top, hook mid-canvas very large",
    "hook in massive weight occupying full width, subheading tiny underneath",
    "hook split across two lines with line break mid-phrase for drama",
]

_ACCENT_USAGES = [
    "thick vertical bar on the left edge",
    "horizontal rule between headline and supporting text",
    "large faint glow circle behind the typography",
    "thin top-of-segment border stripe",
    "underline beneath the hook only",
    "bottom-left corner bracket shape",
    "diagonal stripe across the background",
    "badge pill above the headline",
    "grid of small dots pattern in top-right corner",
    "monochrome: pure dark and white only",
    "thick bottom border stripe",
    "accent fills the entire left 8px border",
    "accent colour used only on supporting text, everything else white",
    "glowing orb behind the main text at 18% opacity",
    "two overlapping rounded rectangles as glass-morphism panels",
    "thin angled rule crossing the canvas diagonally at 15 degrees",
    "large hollow circle outline in the background at 8% opacity",
    "neon-style glow on the hook text using brand accent",
]

_BG_TREATMENTS = [
    "solid near-black #05070b",
    "very dark navy #050a14",
    "pure black #000000",
    "deep dark purple-black #08030f",
    "gradient from #05070b to #0d0d0d top to bottom",
    "dark with one large faint radial glow in brand accent at 12% opacity center",
    "dark with subtle horizontal grid lines at 4% opacity",
    "dark with a single diagonal gradient band of brand accent at 8%",
    "dark with two-tone horizontal split at 55% height",
    "deep charcoal #0a0a0f with soft vignette edges",
    "near-black with a glass panel overlay in the text zone at 8% white",
    "dark with large radial brand accent glow top-right corner",
    "dark gradient from #06070d bottom-left to #12071a top-right",
    "matte dark with textured dot grid at 3% opacity",
]

_DECORATIVE_ELEMENTS = [
    "one large faint circle behind the typography",
    "two overlapping faint circles at different opacities",
    "thin horizontal rules separating sections",
    "small dot grid pattern in top-right corner",
    "no decoration, pure content only",
    "thin diagonal line from top-right to mid-left",
    "accent rectangle stripe at top of canvas",
    "small scattered rectangles at low opacity",
    "large faint rectangle outline only",
    "corner bracket lines in opposite corners",
    "concentric circles at low opacity behind the text",
    "single large triangle clipped to the canvas edge",
    "three stacked horizontal stripes at 6% opacity bottom-right",
    "glass-style rounded rectangle panel behind the main text at 10% white",
    "two gradient-overlay shapes creating depth behind the text zone",
    "large brand-accent orb at 14% opacity blurred behind the hook",
    "subtle noise-like pattern from many tiny 2px rectangles at 4% opacity",
]

_TYPOGRAPHY_STYLES = [
    "Bebas Neue for headlines, Syne for body",
    "Bebas Neue for hook only, all other text in Syne",
    "all Bebas Neue at different sizes and letter spacings",
    "all Syne at varied weights",
    "Bebas Neue headline with wide letterSpacing on subheading",
    "Bebas Neue at lineHeight 0.85 for tight poster impact",
    "Syne 500 weight for everything, clean SaaS feel",
    "alternating Bebas Neue and Syne",
    "Bebas Neue hook with negative letterSpacing and tight lineHeight",
    "Syne 700 for hook, Syne 300 for subheading",
    "Bebas Neue at lineHeight 0.78 and letterSpacing -2 for aggressive poster look",
    "Syne 800 for hook at large size, Syne 400 italic feel for subheading",
]

# Additional vocabulary for hero_media AI prompts
_MEDIA_COMPOSITIONS = [
    "full bleed cinematic background with dramatic lighting sweep",
    "oversized product/person image cropped dramatically off-axis",
    "left safe text zone with right-heavy media focal point",
    "right safe text zone with left-heavy media focal point",
    "huge faded silhouette that bleeds into the background",
    "diagonal editorial image panel with gradient transition",
    "floating glass-frame image with glow halo behind it",
    "luxury device or dashboard frame with ambient glow",
    "horizontal image band blended into dark background",
    "image escaping toward one edge with gradient dissolve",
    "dark atmospheric scene with image at 70% opacity blended",
    "split-screen with left dark panel and right vivid image",
    "image in oversized rounded frame with brand accent border",
    "cinematic widescreen crop centered with heavy vignette overlay",
]

_MEDIA_ATMOSPHERES = [
    "deep radial glow in brand accent behind the image",
    "large soft orb at 20% opacity bottom-left corner",
    "two overlapping gradient orbs creating depth atmosphere",
    "horizontal light sweep across the top third",
    "dark scrim gradient from transparent to 70% black over image",
    "subtle grid overlay at 4% opacity on the image",
    "vignette: dark edges, bright center",
    "brand accent glow bleeding from the bottom edge upward",
    "double orb: one large at 12% center, one small at 28% brand accent top-right",
    "cinematic horizontal gradient band across the image mid-point",
]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _composition_spec() -> Dict[str, str]:
    return {
        "layout_structure":    random.choice(_LAYOUT_STRUCTURES),
        "text_hierarchy":      random.choice(_TEXT_HIERARCHIES),
        "accent_usage":        random.choice(_ACCENT_USAGES),
        "bg_treatment":        random.choice(_BG_TREATMENTS),
        "decorative_elements": random.choice(_DECORATIVE_ELEMENTS),
        "typography_style":    random.choice(_TYPOGRAPHY_STYLES),
        "seed":                str(time.time_ns()),
    }


def _fields_for_generation(segment_type: str) -> List[str]:
    """
    hero_text intentionally varies each generation for diversity:
      - hook only
      - hook + subheading
      - subheading only (rare)
    All other segment types use their full field list.
    """
    if segment_type == "hero_text":
        return random.choice([
            ["hook"],
            ["hook", "subheading"],
            ["hook", "subheading"],   # weighted: hook+sub more common
            ["subheading"],
        ])
    return SEGMENT_FIELDS.get(segment_type, [])


def _unique_token() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def _brand_seed(brand_name: str, segment_type: str) -> int:
    return abs(hash(f"{brand_name}:{segment_type}")) % 10_000


def _num(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except Exception:
        return fallback


def _int(value: Any, fallback: int) -> int:
    try:
        return int(float(value))
    except Exception:
        return fallback


def extract_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end   = text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError(f"No JSON found. Raw: {text[:600]}")
    return json.loads(text[start:end + 1])


def _extract_blueprint_positions(blueprint: Dict[str, Any]) -> Dict[str, tuple[int, int]]:
    out: Dict[str, tuple[int, int]] = {}
    for shape in blueprint.get("shapes", []):
        if shape.get("type") == "text" and shape.get("dataField"):
            out[str(shape["dataField"])] = (
                int(shape.get("x", 0)),
                int(shape.get("y", 0)),
            )
    return out


def _clamp_shape(shape: dict, canvas_width: int, segment_height: int) -> dict:
    x = max(0, min(_int(shape.get("x"), PAD), canvas_width - 10))
    y = max(0, min(_int(shape.get("y"), PAD), segment_height - 10))
    width  = max(10, _int(shape.get("width"),  100))
    height = max(10, _int(shape.get("height"),  40))
    width  = min(width,  canvas_width  - x)
    height = min(height, segment_height - y)
    return {**shape, "x": round(x), "y": round(y), "width": round(width), "height": round(height)}


def _has_background_shape(shapes: List[dict], canvas_width: int, segment_height: int) -> bool:
    for shape in shapes:
        if not isinstance(shape, dict):
            continue
        if shape.get("type") not in {"rectangle", "rounded-rect", "gradient-overlay"}:
            continue
        x = _int(shape.get("x"), 9999)
        y = _int(shape.get("y"), 9999)
        w = _int(shape.get("width"),  0)
        h = _int(shape.get("height"), 0)
        if x <= 8 and y <= 8 and w >= canvas_width * 0.85 and h >= segment_height * 0.75:
            return True
    return False


def _random_section_background(canvas_width: int, segment_height: int, token: str) -> List[dict]:
    """
    Pick a rich dark background: solid, gradient, or glass-style.
    All three options are premium dark — no whites or light fills.
    """
    choices = [
        {
            "id": f"bg-solid-{token}",
            "type": "rounded-rect",
            "x": 0, "y": 0,
            "width": canvas_width, "height": segment_height,
            "backgroundColor": random.choice(["#05070b", "#000000", "#070912", "#08030f", "#060610"]),
            "borderRadius": 0,
            "zIndex": 0, "opacity": 1,
        },
        {
            "id": f"bg-grad-{token}",
            "type": "gradient-overlay",
            "x": 0, "y": 0,
            "width": canvas_width, "height": segment_height,
            "gradientColors": [
                {"stop": 0, "color": "#05070b"},
                {"stop": 1, "color": "rgba(124,58,237,0.18)"},
            ],
            "gradientAngle": random.choice([45, 90, 135, 180]),
            "backgroundColor": "transparent",
            "borderWidth": 0,
            "zIndex": 0, "opacity": 1,
        },
        {
            # Two-tone split
            "id": f"bg-split-{token}",
            "type": "gradient-overlay",
            "x": 0, "y": 0,
            "width": canvas_width, "height": segment_height,
            "gradientColors": [
                {"stop": 0,    "color": "#06070d"},
                {"stop": 0.52, "color": "#0d0820"},
                {"stop": 1,    "color": "#060610"},
            ],
            "gradientAngle": random.choice([160, 200, 225]),
            "backgroundColor": "transparent",
            "borderWidth": 0,
            "zIndex": 0, "opacity": 1,
        },
    ]
    return [random.choice(choices)]


def _make_shape_id(shape: dict, segment_type: str, token: str, index: int) -> str:
    current = shape.get("id")
    if current:
        return str(current)
    return f"ai-{segment_type}-{token}-{index}"


# ─────────────────────────────────────────────────────────────────────────────
# Normalisation
# ─────────────────────────────────────────────────────────────────────────────

def normalize_text_shape(
    shape: dict, index: int, segment_type: str,
    canvas_width: int, segment_height: int, token: str,
    active_fields: List[str],
) -> Optional[dict]:
    data_field = str(shape.get("dataField") or "")
    if data_field not in active_fields:
        return None
    min_w, min_h = MIN_BOX.get(data_field, (280, 50))
    base: Dict[str, Any] = {
        "id":         _make_shape_id(shape, segment_type, token, index),
        "type":       "text",
        "x":          max(0, round(_num(shape.get("x"), PAD))),
        "y":          max(0, round(_num(shape.get("y"), PAD))),
        "width":      max(round(_num(shape.get("width"),  min_w)), min_w),
        "height":     max(round(_num(shape.get("height"), min_h)), min_h),
        "zIndex":     max(_int(shape.get("zIndex"), index + 10), 5),
        "opacity":    max(0.0, min(_num(shape.get("opacity"), 1.0), 1.0)),
        "dataField":  data_field,
        "text":       "",
        "customText": None,
        "fontSize":     max(_int(shape.get("fontSize"), 32), MIN_FONT.get(data_field, 22)),
        "fontFamily":   shape.get("fontFamily", "Bebas Neue"),
        "fontWeight":   _int(shape.get("fontWeight"), 700),
        "textColor":    shape.get("textColor", "#ffffff"),
        "textAlign":    shape.get("textAlign", "left"),
        "lineHeight":   _num(shape.get("lineHeight"), 1.0),
        "letterSpacing":_num(shape.get("letterSpacing"), 0),
        "padding":      max(_int(shape.get("padding"), 0), 8),
        "backgroundColor": shape.get("backgroundColor", "transparent"),
        "borderColor":     shape.get("borderColor",     "transparent"),
        "borderWidth":     _int(shape.get("borderWidth"), 0),
        "shadowBlur":      _int(shape.get("shadowBlur"), 0),
        "shadowX":         _int(shape.get("shadowX"), 0),
        "shadowY":         _int(shape.get("shadowY"), 0),
        "shadowColor":     shape.get("shadowColor", "#000000"),
    }
    return _clamp_shape(base, canvas_width, segment_height)


def normalize_media_shape(
    shape: dict, index: int,
    canvas_width: int, segment_height: int, token: str,
) -> Optional[dict]:
    if not isinstance(shape, dict):
        return None
    shape_type = str(shape.get("type") or "image")
    if shape_type not in {"image", "rectangle", "rounded-rect", "circle", "gradient-overlay"}:
        return None

    raw_z = _int(shape.get("zIndex"), index)
    z_index = max(0, min(raw_z, 18))

    base: Dict[str, Any] = {
        "id":       _make_shape_id(shape, "hero_media", token, index),
        "type":     shape_type,
        "x":        round(_num(shape.get("x"), 0)),
        "y":        round(_num(shape.get("y"), 0)),
        "width":    max(10, round(_num(shape.get("width"),  canvas_width))),
        "height":   max(10, round(_num(shape.get("height"), segment_height))),
        "zIndex":   z_index,
        "opacity":  max(0.0, min(_num(shape.get("opacity"), 1.0), 1.0)),
        "backgroundColor": shape.get("backgroundColor", "transparent"),
        "borderColor":     shape.get("borderColor",     "transparent"),
        "borderWidth":     _int(shape.get("borderWidth"), 0),
        "shadowBlur":      _int(shape.get("shadowBlur"), 0),
        "shadowX":         _int(shape.get("shadowX"), 0),
        "shadowY":         _int(shape.get("shadowY"), 0),
        "shadowColor":     shape.get("shadowColor", "#000000"),
    }
    if shape_type == "image":
        base.update({
            "src":                None,
            "slotKey":            "hero_person",
            "slotLabel":          "Hero Image",
            "slotType":           "image",
            "slotRole":           "hero",
            "fit":                shape.get("fit", "cover"),
            "radius":             _int(shape.get("radius"), 0),
            "rotation":           _num(shape.get("rotation"), 0),
            "slotVisibleWhenEmpty": False,
        })
    elif shape_type in {"rounded-rect", "rectangle", "circle"}:
        base["borderRadius"] = _int(shape.get("borderRadius"), 0)
    elif shape_type == "gradient-overlay":
        base["gradientColors"] = shape.get("gradientColors", [])
        base["gradientAngle"]  = _int(shape.get("gradientAngle"), 180)
    return _clamp_shape(base, canvas_width, segment_height)


def normalize_design_shape(
    shape: dict, index: int, segment_type: str,
    canvas_width: int, segment_height: int, token: str,
    active_fields: List[str],
) -> Optional[dict]:
    if not isinstance(shape, dict):
        return None
    shape_type = str(shape.get("type") or "text")
    if shape_type == "text":
        return normalize_text_shape(shape, index, segment_type, canvas_width, segment_height, token, active_fields)
    if shape_type in {"image", "button"}:
        return None
    allowed = {"rectangle", "rounded-rect", "circle", "line", "triangle", "gradient-overlay"}
    if shape_type not in allowed:
        return None
    base: Dict[str, Any] = {
        "id":      _make_shape_id(shape, segment_type, token, index),
        "type":    shape_type,
        "x":       max(0, round(_num(shape.get("x"), PAD))),
        "y":       max(0, round(_num(shape.get("y"), PAD))),
        "width":   max(10, round(_num(shape.get("width"),  300))),
        "height":  max(10, round(_num(shape.get("height"),  80))),
        "zIndex":  _int(shape.get("zIndex"), index + 1),
        "opacity": max(0.0, min(_num(shape.get("opacity"), 1.0), 1.0)),
        "backgroundColor": shape.get("backgroundColor", "transparent"),
        "borderColor":     shape.get("borderColor",     "transparent"),
        "borderWidth":     _int(shape.get("borderWidth"), 0),
        "shadowBlur":      _int(shape.get("shadowBlur"), 0),
        "shadowX":         _int(shape.get("shadowX"), 0),
        "shadowY":         _int(shape.get("shadowY"), 0),
        "shadowColor":     shape.get("shadowColor", "#000000"),
    }
    if shape_type in {"rounded-rect", "rectangle", "circle"}:
        base["borderRadius"] = _int(shape.get("borderRadius"), 0)
        if "gradientColors" in shape:
            base["gradientColors"] = shape["gradientColors"]
            base["gradientAngle"]  = _int(shape.get("gradientAngle"), 90)
    elif shape_type == "gradient-overlay":
        base["gradientColors"] = shape.get("gradientColors", [])
        base["gradientAngle"]  = _int(shape.get("gradientAngle"), 180)
    return _clamp_shape(base, canvas_width, segment_height)


# ─────────────────────────────────────────────────────────────────────────────
# Overlap resolution
# ─────────────────────────────────────────────────────────────────────────────

def _overlaps(a: dict, b: dict) -> bool:
    return not (
        float(a.get("x", 0)) + float(a.get("width",  0)) <= float(b.get("x", 0))
        or float(a.get("x", 0)) >= float(b.get("x", 0)) + float(b.get("width",  0))
        or float(a.get("y", 0)) + float(a.get("height", 0)) <= float(b.get("y", 0))
        or float(a.get("y", 0)) >= float(b.get("y", 0)) + float(b.get("height", 0))
    )


def resolve_text_overlaps(
    shapes: List[dict], canvas_width: int, segment_height: int,
) -> List[dict]:
    result: List[dict] = []
    for shape in sorted(shapes, key=lambda s: int(s.get("zIndex", 1))):
        if shape.get("type") != "text":
            result.append(shape)
            continue
        adjusted = {**shape}
        for placed in result:
            if placed.get("type") != "text":
                continue
            if not _overlaps(adjusted, placed):
                continue
            pushed_y = int(placed.get("y", 0)) + int(placed.get("height", 0)) + 10
            if pushed_y + int(adjusted.get("height", 40)) <= segment_height:
                adjusted["y"] = pushed_y
            else:
                pushed_x = int(placed.get("x", 0)) + int(placed.get("width", 0)) + 12
                if pushed_x + int(adjusted.get("width", 200)) <= canvas_width:
                    adjusted["x"] = pushed_x
                else:
                    adjusted["height"] = max(20, segment_height - int(adjusted.get("y", 0)) - 8)
        result.append(_clamp_shape(adjusted, canvas_width, segment_height))
    return sorted(result, key=lambda s: int(s.get("zIndex", 1)))


def _similarity_score(
    shapes: List[dict],
    blueprint_positions: Dict[str, tuple[int, int]],
    tolerance: int = 60,
) -> float:
    """
    Returns 0.0–1.0 measuring how closely the AI layout mirrors the blueprint.
    Raised threshold to 0.80 — we only block outright copies, not creative layouts.
    """
    if not blueprint_positions:
        return 0.0
    matches = 0
    checked = 0
    for shape in shapes:
        if shape.get("type") != "text":
            continue
        field = shape.get("dataField")
        if field not in blueprint_positions:
            continue
        bx, by = blueprint_positions[field]
        if abs(int(shape.get("x", 0)) - bx) <= tolerance and abs(int(shape.get("y", 0)) - by) <= tolerance:
            matches += 1
        checked += 1
    return matches / checked if checked else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_media_segment(
    data: Dict[str, Any], canvas_width: int, segment_type: str, token: str,
) -> Dict[str, Any]:
    segment_height = _int(data.get("segment_height"), 430)
    raw_shapes = data.get("shapes")
    if not isinstance(raw_shapes, list) or not raw_shapes:
        raise ValueError("Hero media returned empty shapes")

    shapes: List[dict] = []
    for index, raw in enumerate(raw_shapes):
        shape = normalize_media_shape(raw, index, canvas_width, segment_height, token)
        if shape:
            shapes.append(shape)

    if not shapes:
        raise ValueError("No valid hero media shapes after validation")

    # Ensure exactly 1 image slot
    image_shapes = [s for s in shapes if s.get("type") == "image"]
    if len(image_shapes) == 0:
        # Inject a full-canvas image slot
        shapes.append({
            "id":       f"ai-hero_media-{token}-injected-img",
            "type":     "image",
            "x": 0, "y": 0,
            "width":  canvas_width, "height": segment_height,
            "src":    None,
            "slotKey":   "hero_person",
            "slotLabel": "Hero Image",
            "slotType":  "image",
            "slotRole":  "hero",
            "fit":    "cover",
            "radius": 0,
            "rotation": 0.0,
            "zIndex": 4,
            "opacity": 0.92,
            "slotVisibleWhenEmpty": False,
            "backgroundColor": "transparent",
            "borderColor": "transparent",
            "borderWidth": 0,
            "shadowBlur": 0, "shadowX": 0, "shadowY": 0, "shadowColor": "#000000",
        })
    elif len(image_shapes) > 1:
        # Keep only the largest image shape, remove the rest
        largest = max(image_shapes, key=lambda s: s.get("width", 0) * s.get("height", 0))
        shapes = [s for s in shapes if s.get("type") != "image" or s is largest]

    # Ensure a background exists
    if not _has_background_shape(shapes, canvas_width, segment_height):
        shapes = _random_section_background(canvas_width, segment_height, token) + shapes

    # Canvas bounds check
    for shape in shapes:
        x = int(shape.get("x", 0))
        y = int(shape.get("y", 0))
        w = int(shape.get("width",  0))
        h = int(shape.get("height", 0))
        if x < 0 or y < 0 or x + w > canvas_width + 1 or y + h > segment_height + 1:
            # Clamp rather than raise — media shapes can be oversized deliberately
            shape.update(_clamp_shape(shape, canvas_width, segment_height))

    return {
        "name":                  data.get("name") or "AI Premium Hero Media",
        "description":           data.get("description") or "AI-composed hero media layer",
        "segment_type":          "hero_media",
        "internal_segment_type": "hero_media",
        "segment_height":        segment_height,
        "shapes": sorted(shapes, key=lambda s: int(s.get("zIndex", 0))),
    }


def validate_segment(
    data: Dict[str, Any], canvas_width: int, segment_type: str,
    token: str, blueprint_positions: Dict[str, tuple[int, int]],
    active_fields: List[str],
) -> Dict[str, Any]:
    segment_height = _int(data.get("segment_height"), 0)
    if segment_height < 80 or segment_height > 900:
        raise ValueError(f"Invalid segment_height={segment_height} for {segment_type}")

    raw_shapes = data.get("shapes")
    if not isinstance(raw_shapes, list) or not raw_shapes:
        raise ValueError(f"Empty shapes for {segment_type}")

    # Strip image and button shapes (not allowed in text segments)
    raw_shapes = [
        s for s in raw_shapes
        if isinstance(s, dict) and s.get("type") not in {"image", "button"}
    ]
    # Strip text shapes with wrong dataField
    raw_shapes = [
        s for s in raw_shapes
        if not (s.get("type") == "text" and s.get("dataField") not in active_fields)
    ]
    # Inject background if missing
    if not _has_background_shape(raw_shapes, canvas_width, segment_height):
        raw_shapes = _random_section_background(canvas_width, segment_height, token) + raw_shapes

    seen_fields: set = set()
    normalized: List[dict] = []
    for index, raw in enumerate(raw_shapes):
        data_field = raw.get("dataField")
        if raw.get("type") == "text" and data_field:
            if data_field not in active_fields:
                continue
            if data_field in seen_fields:
                continue
            seen_fields.add(data_field)
        shape = normalize_design_shape(raw, index, segment_type, canvas_width, segment_height, token, active_fields)
        if shape:
            normalized.append(shape)

    if not normalized:
        raise ValueError(f"No valid shapes after normalisation for {segment_type}")

    final = resolve_text_overlaps(normalized, canvas_width, segment_height)

    for shape in final:
        x = int(shape.get("x", 0))
        y = int(shape.get("y", 0))
        w = int(shape.get("width",  0))
        h = int(shape.get("height", 0))
        if x < 0 or y < 0 or x + w > canvas_width or y + h > segment_height:
            raise ValueError(
                f"Shape escaped canvas: id={shape.get('id')} "
                f"x={x} y={y} w={w} h={h} canvas={canvas_width}x{segment_height}"
            )

    # Similarity check — only blocks outright copies (>80%)
    if segment_type != "footer":
        score = _similarity_score(final, blueprint_positions)
        if score > 0.80:
            raise ValueError(f"AI copied blueprint too closely similarity={score:.0%}")
    else:
        score = 0.0

    logger.info(
        "segment OK: type=%s height=%d shapes=%d similarity=%.0f%%",
        segment_type, segment_height, len(final), score * 100,
    )
    return {
        "name":                  data.get("name") or f"AI {segment_type.title()} Segment",
        "description":           data.get("description") or "",
        "segment_type":          PUBLIC_TYPE.get(segment_type, segment_type),
        "internal_segment_type": segment_type,
        "segment_height":        segment_height,
        "shapes":                final,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builders
# ─────────────────────────────────────────────────────────────────────────────

def build_prompt(
    *, segment_type: str, brand_name: str, brand_color: str,
    tone_name: str, canvas_width: int, orientation: str,
    blueprint: Dict[str, Any], spec: Dict[str, str],
    blueprint_positions: Dict[str, tuple[int, int]],
    active_fields: List[str],
) -> str:
    segment_height = int(blueprint["segment_height"])

    field_names = ", ".join(
        shape["dataField"]
        for shape in blueprint.get("shapes", [])
        if shape.get("type") == "text" and shape.get("dataField")
    )
    forbidden_lines = [
        f"  {field}: blueprint had x={x} y={y}; place farther than 80px from this"
        for field, (x, y) in blueprint_positions.items()
        if field in active_fields
    ]
    forbidden_block = "\n".join(forbidden_lines) or "  no forbidden text positions"
    min_font_line = ", ".join(
        f"{field}>={MIN_FONT[field]}px"
        for field in active_fields if field in MIN_FONT
    )

    footer_extra = ""
    if segment_type == "footer":
        footer_extra = """
FOOTER RULES:
- Footer must be a simple contact strip only.
- No logo. No company title block. No social clutter.
- Use only contact_row1, contact_row2, and business_website.
- Vary: alignment, line placement, background, spacing, typography each generation.
- Keep it clean, readable, aligned, and anchored.
""".strip()

    hero_extra = ""
    if segment_type == "hero_text":
        hero_extra = """
HERO TEXT RULES:
- This is the text/composition layer only. NO image shapes. NO button shapes.
- Use ONLY the allowed fields listed above.
- Text must be high-contrast against a dark background (a separate image layer sits behind).
- Add a semi-transparent glass-panel or gradient overlay behind the text for readability.
- Be creative: the background can have glow orbs, gradient bands, or glass rectangles.
""".strip()

    return f"""
You are a senior marketing art director and production canvas layout engineer.
Your output must be COMMERCIAL QUALITY: dark premium aesthetic, glass panels,
glow orbs, layered depth, rich decorative shapes. Not plain. Not minimal.

MISSION
Design a premium editable {segment_type} segment.
Use the blueprint only as field reference. Do NOT copy its exact positions.
Make a fresh, commercial, visually rich composition every time.

CANVAS
width: {canvas_width}
height: {segment_height}
origin: top-left
Every shape must stay inside this canvas.

BRAND
name: {brand_name}
tone: {tone_name}
accent: {brand_color}
Use the literal string "__BRAND_ACCENT__" for all brand accent colour values.

DESIGN SPEC (follow this creative brief)
layout_structure:    {spec["layout_structure"]}
text_hierarchy:      {spec["text_hierarchy"]}
accent_usage:        {spec["accent_usage"]}
background:          {spec["bg_treatment"]}
decorative_elements: {spec["decorative_elements"]}
typography_style:    {spec["typography_style"]}
uniqueness_seed:     {spec["seed"]}

ALLOWED DATA FIELDS FOR THIS GENERATION
{chr(10).join("  - " + field for field in active_fields)}

REFERENCE FIELDS (from blueprint, for field naming only)
{field_names or "none"}

FORBIDDEN POSITIONS (place text AT LEAST 80px away from these)
{forbidden_block}

RULES
1. Return raw JSON only. No markdown. No prose. No code fences.
2. Use each dataField at most once.
3. Text shapes must include dataField and "text": "".
4. Do not hardcode marketing copy in text shapes.
5. Do NOT generate image shapes in text/content segments.
6. Do NOT generate button shapes.
7. ALWAYS include a full-section background shape (rounded-rect or gradient-overlay).
8. ADD decorative shapes: glow circles, glass panels, accent lines, gradient overlays.
   These make the design commercial — do not skip them.
9. segment_height must be exactly {segment_height}.
10. Minimum font sizes: {min_font_line or "use large readable typography"}.
11. All shapes need: id, type, x, y, width, height, zIndex, opacity.
12. Allowed shape types: text, rectangle, rounded-rect, circle, line, triangle, gradient-overlay.
13. zIndex layering: background=0, decoration=1-4, content panels=5-9, text=10+.

DECORATION GUIDANCE (commercial look checklist):
- At least ONE glow orb: large circle, brand accent or deep purple, opacity 0.10-0.18
- At least ONE glass panel behind text: rounded-rect, white 0.06-0.10 opacity
- At least ONE accent line or stripe: thin rectangle in brand accent
- Background must be dark: #05070b, #000000, #08030f, or dark gradient
- Text must be #ffffff or near-white. Never dark text on dark background.

{hero_extra}

{footer_extra}

OUTPUT FORMAT
{{
  "name": "unique descriptive segment name",
  "description": "one-line composition strategy",
  "segment_type": "{segment_type}",
  "segment_height": {segment_height},
  "shapes": []
}}
""".strip()


def build_hero_media_prompt(
    *, brand_name: str, brand_color: str, tone_name: str,
    canvas_width: int, segment_height: int, orientation: str,
    nonce: str,
) -> str:
    composition = random.choice(_MEDIA_COMPOSITIONS)
    atmosphere  = random.choice(_MEDIA_ATMOSPHERES)

    return f"""
You are a premium AI visual layout engine and senior marketing art director.

MISSION
Compose a HERO MEDIA background section: image, atmosphere, glow, depth.
This is NOT a text layer. NO text shapes. NO button shapes.
Hero text will float above this at zIndex 20+.
Your shapes must stay below zIndex 18.

CANVAS
width: {canvas_width}
height: {segment_height}
orientation: {orientation}
origin: top-left

BRAND
name: {brand_name}
accent: {brand_color}
Use "__BRAND_ACCENT__" for all brand accent colour values.

CREATIVE BRIEF
composition_style: {composition}
atmosphere: {atmosphere}

Z-INDEX CONTRACT
background:              0
decorative atmosphere:   1-3
image/media slot:        4-8
overlays and scrims:     9-14
foreground decoration:   15-18
RESERVED for hero text:  20+

ALLOWED SHAPE TYPES
image, rectangle, rounded-rect, circle, gradient-overlay

IMAGE RULES
- Include EXACTLY ONE image shape.
- It must have: "slotKey": "hero_person", "slotType": "image", "slotRole": "hero", "fit": "cover", "src": null
- It can be full-bleed, off-center, cropped, oversized — be creative with its placement.
- Do NOT use placeholder image URLs. Always set src to null.

REQUIRED LAYERS (minimum):
1. One full-canvas background (rounded-rect or gradient-overlay), zIndex 0
2. One or two atmospheric glow orbs (circles, brand accent or deep purple, opacity 0.12-0.22), zIndex 1-3
3. One image shape, zIndex 4-8
4. One gradient scrim/overlay over or around the image for readability, zIndex 9-14
5. One or two foreground decoration shapes (accent line, glass panel, glow), zIndex 15-18

OUTPUT RULES
- Return raw JSON only. No markdown. No explanation. No code fences.
- segment_height must be exactly {segment_height}.
- Include 6 to 12 shapes.
- Include exactly one image shape.
- All shapes need: id, type, x, y, width, height, zIndex, opacity.

UNIQUENESS TOKEN: {nonce}

OUTPUT FORMAT
{{
  "name": "AI Premium Hero Media",
  "description": "one-line composition strategy",
  "segment_type": "hero_media",
  "segment_height": {segment_height},
  "shapes": []
}}
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def generate_ai_segment(
    *, segment_type: str, brand_name: str, brand_color: str,
    tone_name: str, canvas_width: int = CANVAS_WIDTH_DEFAULT,
    segment_height: Optional[int] = None, orientation: str = "portrait",
) -> Dict[str, Any]:
    # Resolve internal type
    internal_type = TYPE_ALIAS.get(segment_type, segment_type)

    token = _unique_token()
    seed  = _brand_seed(brand_name, internal_type) + random.randint(0, 999_999)

    # ── Hero media: AI-composed via LLM ──────────────────────────────────────
    if internal_type == "hero_media":
        blueprint = get_blueprint("hero_media", brand_seed=seed)
        if not blueprint:
            raise ValueError("No blueprint found for: hero_media")
        if segment_height:
            blueprint["segment_height"] = segment_height

        media_height = _int(
            blueprint.get("segment_height"),
            1080 if orientation == "landscape" else 860,
        )

        last_error: Optional[Exception] = None
        for attempt, temperature in enumerate([0.95, 1.05, 1.15]):
            nonce = _unique_token()
            try:
                prompt = build_hero_media_prompt(
                    brand_name=brand_name,
                    brand_color=brand_color,
                    tone_name=tone_name,
                    canvas_width=canvas_width,
                    segment_height=media_height,
                    orientation=orientation,
                    nonce=nonce,
                )
                logger.info(
                    "attempt=%d/3 type=hero_media temp=%.2f nonce=%s",
                    attempt + 1, temperature, nonce,
                )
                response = client.chat.completions.create(
                    model=MODEL,
                    temperature=temperature,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a premium AI visual layout engine. "
                                "Return valid JSON only. No markdown. No code fences. "
                                "Generate original cinematic canvas compositions. "
                                "Include exactly one image shape with slotKey hero_person."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
                raw    = response.choices[0].message.content or ""
                parsed = extract_json(raw)
                result = validate_media_segment(parsed, canvas_width, "hero_media", token)
                logger.info("SUCCESS attempt=%d type=hero_media", attempt + 1)
                return result
            except Exception as exc:
                last_error = exc
                logger.warning("FAIL attempt=%d type=hero_media error=%s", attempt + 1, exc)

        raise RuntimeError(
            f"All 3 hero_media generation attempts failed. Last error: {last_error}"
        )

    # ── Text/content segments ─────────────────────────────────────────────────
    if internal_type not in SEGMENT_FIELDS:
        raise ValueError(f"Unsupported segment type: '{segment_type}' → '{internal_type}'")

    blueprint = get_blueprint(internal_type, brand_seed=seed)
    if not blueprint:
        raise ValueError(f"No blueprint found for: {internal_type}")
    if segment_height:
        blueprint["segment_height"] = segment_height

    active_fields      = _fields_for_generation(internal_type)
    blueprint_positions = _extract_blueprint_positions(blueprint)

    last_error = None
    for attempt, temperature in enumerate([0.95, 1.0, 1.08]):
        spec   = _composition_spec()
        prompt = build_prompt(
            segment_type=internal_type,
            brand_name=brand_name,
            brand_color=brand_color,
            tone_name=tone_name,
            canvas_width=canvas_width,
            orientation=orientation,
            blueprint=blueprint,
            spec=spec,
            blueprint_positions=blueprint_positions,
            active_fields=active_fields,
        )
        logger.info(
            "attempt=%d/3 type=%s fields=%s temp=%.2f",
            attempt + 1, internal_type, active_fields, temperature,
        )
        try:
            response = client.chat.completions.create(
                model=MODEL,
                temperature=temperature,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a premium marketing art director. "
                            "Return valid JSON only. No markdown. No code fences. "
                            "Never generate image or button shapes. "
                            "Always include glow orbs, glass panels, and accent decorations. "
                            "Never copy blueprint positions exactly."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            raw    = response.choices[0].message.content or ""
            parsed = extract_json(raw)
            result = validate_segment(
                parsed, canvas_width, internal_type, token, blueprint_positions, active_fields,
            )
            logger.info("SUCCESS attempt=%d type=%s", attempt + 1, internal_type)
            return result
        except Exception as exc:
            last_error = exc
            logger.warning("FAIL attempt=%d type=%s error=%s", attempt + 1, internal_type, exc)

    raise RuntimeError(
        f"All 3 generation attempts failed for '{internal_type}'. Last error: {last_error}"
    )