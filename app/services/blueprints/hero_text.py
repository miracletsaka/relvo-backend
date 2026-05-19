from __future__ import annotations

import random
from typing import Any, Dict, List


TEXT_COMPOSITIONS: List[str] = [
    "massive_left_headline",
    "bottom_left_cinematic",
    "center_editorial",
    "right_aligned_luxury",
    "top_left_campaign",
    "split_title_stack",
    "badge_plus_headline",
    "minimal_statement",
    "poster_crop_headline",
]

FONT_SYSTEMS: List[Dict[str, Any]] = [
    {
        "name": "bebas_syne_premium",
        "headline_font": "Bebas Neue",
        "body_font": "Syne",
        "headline_weight": 700,
        "body_weight": 400,
        "headline_tracking": -1,
    },
    {
        "name": "bebas_bold_campaign",
        "headline_font": "Bebas Neue",
        "body_font": "Syne",
        "headline_weight": 700,
        "body_weight": 500,
        "headline_tracking": 0.5,
    },
    {
        "name": "syne_clean_saas",
        "headline_font": "Syne",
        "body_font": "Syne",
        "headline_weight": 800,
        "body_weight": 400,
        "headline_tracking": -1.6,
    },
]

TEXT_COLORS: List[Dict[str, str]] = [
    {
        "main": "#FFFFFF",
        "soft": "rgba(255,255,255,0.78)",
        "muted": "rgba(255,255,255,0.52)",
        "panel": "rgba(0,0,0,0.36)",
        "border": "rgba(255,255,255,0.14)",
    },
    {
        "main": "#F8FAFC",
        "soft": "rgba(248,250,252,0.74)",
        "muted": "rgba(248,250,252,0.48)",
        "panel": "rgba(5,8,22,0.52)",
        "border": "rgba(255,255,255,0.10)",
    },
    {
        "main": "#FFFFFF",
        "soft": "rgba(255,255,255,0.7)",
        "muted": "rgba(255,255,255,0.44)",
        "panel": "rgba(10,10,10,0.48)",
        "border": "rgba(255,255,255,0.16)",
    },
]


def _pick(items: List[Any]) -> Any:
    return random.choice(items)


def _shape_id(prefix: str) -> str:
    return f"hero-text-{prefix}-{random.randint(1000, 9999)}"


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def _headline_size(canvas_width: int, orientation: str) -> int:
    if orientation == "landscape" or canvas_width >= 1600:
        return random.choice([104, 116, 128, 142, 156])
    return random.choice([78, 88, 98, 112])


def _subheading_size(canvas_width: int, orientation: str) -> int:
    if orientation == "landscape" or canvas_width >= 1600:
        return random.choice([28, 32, 36, 40])
    return random.choice([26, 28, 30, 32])


def _layout_boxes(
    composition: str,
    canvas_width: int,
    height: int,
) -> Dict[str, Dict[str, int | str]]:
    left_x = int(canvas_width * 0.06)
    right_x = int(canvas_width * 0.53)
    max_left_w = int(canvas_width * 0.48)
    max_center_w = int(canvas_width * 0.68)
    max_right_w = int(canvas_width * 0.4)

    if composition == "massive_left_headline":
        return {
            "align": {"value": "left"},
            "panel": {
                "x": left_x - 34,
                "y": int(height * 0.18),
                "width": max_left_w + 88,
                "height": int(height * 0.54),
            },
            "eyebrow": {
                "x": left_x,
                "y": int(height * 0.22),
                "width": int(max_left_w * 0.7),
                "height": 44,
            },
            "hook": {
                "x": left_x,
                "y": int(height * 0.29),
                "width": max_left_w,
                "height": int(height * 0.24),
            },
            "subheading": {
                "x": left_x,
                "y": int(height * 0.58),
                "width": int(max_left_w * 0.82),
                "height": 96,
            },
        }

    if composition == "bottom_left_cinematic":
        return {
            "align": {"value": "left"},
            "panel": {
                "x": left_x - 34,
                "y": int(height * 0.5),
                "width": max_left_w + 110,
                "height": int(height * 0.34),
            },
            "eyebrow": {
                "x": left_x,
                "y": int(height * 0.54),
                "width": int(max_left_w * 0.72),
                "height": 44,
            },
            "hook": {
                "x": left_x,
                "y": int(height * 0.61),
                "width": max_left_w,
                "height": int(height * 0.18),
            },
            "subheading": {
                "x": left_x,
                "y": int(height * 0.8),
                "width": int(max_left_w * 0.86),
                "height": 76,
            },
        }

    if composition == "center_editorial":
        return {
            "align": {"value": "center"},
            "panel": {
                "x": int((canvas_width - max_center_w) / 2) - 40,
                "y": int(height * 0.2),
                "width": max_center_w + 80,
                "height": int(height * 0.48),
            },
            "eyebrow": {
                "x": int((canvas_width - int(max_center_w * 0.5)) / 2),
                "y": int(height * 0.24),
                "width": int(max_center_w * 0.5),
                "height": 44,
            },
            "hook": {
                "x": int((canvas_width - max_center_w) / 2),
                "y": int(height * 0.32),
                "width": max_center_w,
                "height": int(height * 0.22),
            },
            "subheading": {
                "x": int((canvas_width - int(max_center_w * 0.62)) / 2),
                "y": int(height * 0.58),
                "width": int(max_center_w * 0.62),
                "height": 88,
            },
        }

    if composition == "right_aligned_luxury":
        return {
            "align": {"value": "right"},
            "panel": {
                "x": right_x - 44,
                "y": int(height * 0.2),
                "width": max_right_w + 88,
                "height": int(height * 0.48),
            },
            "eyebrow": {
                "x": right_x,
                "y": int(height * 0.24),
                "width": max_right_w,
                "height": 44,
            },
            "hook": {
                "x": right_x,
                "y": int(height * 0.32),
                "width": max_right_w,
                "height": int(height * 0.22),
            },
            "subheading": {
                "x": right_x + int(max_right_w * 0.12),
                "y": int(height * 0.59),
                "width": int(max_right_w * 0.88),
                "height": 88,
            },
        }

    if composition == "top_left_campaign":
        return {
            "align": {"value": "left"},
            "panel": {
                "x": left_x - 28,
                "y": int(height * 0.08),
                "width": max_left_w + 84,
                "height": int(height * 0.45),
            },
            "eyebrow": {
                "x": left_x,
                "y": int(height * 0.12),
                "width": int(max_left_w * 0.7),
                "height": 44,
            },
            "hook": {
                "x": left_x,
                "y": int(height * 0.19),
                "width": max_left_w,
                "height": int(height * 0.22),
            },
            "subheading": {
                "x": left_x,
                "y": int(height * 0.44),
                "width": int(max_left_w * 0.82),
                "height": 88,
            },
        }

    if composition == "poster_crop_headline":
        return {
            "align": {"value": "left"},
            "panel": {
                "x": 0,
                "y": int(height * 0.18),
                "width": int(canvas_width * 0.56),
                "height": int(height * 0.56),
            },
            "eyebrow": {
                "x": left_x,
                "y": int(height * 0.22),
                "width": int(max_left_w * 0.7),
                "height": 44,
            },
            "hook": {
                "x": -12,
                "y": int(height * 0.3),
                "width": int(canvas_width * 0.58),
                "height": int(height * 0.24),
            },
            "subheading": {
                "x": left_x,
                "y": int(height * 0.62),
                "width": int(max_left_w * 0.82),
                "height": 86,
            },
        }

    return {
        "align": {"value": "left"},
        "panel": {
            "x": left_x - 34,
            "y": int(height * 0.22),
            "width": max_left_w + 90,
            "height": int(height * 0.46),
        },
        "eyebrow": {
            "x": left_x,
            "y": int(height * 0.26),
            "width": int(max_left_w * 0.7),
            "height": 44,
        },
        "hook": {
            "x": left_x,
            "y": int(height * 0.34),
            "width": max_left_w,
            "height": int(height * 0.22),
        },
        "subheading": {
            "x": left_x,
            "y": int(height * 0.6),
            "width": int(max_left_w * 0.82),
            "height": 86,
        },
    }


def get(
    brand_seed: int | None = None,
    canvas_width: int = 1920,
    orientation: str = "landscape",
    segment_height: int | None = None,
) -> Dict[str, Any]:
    if brand_seed is not None:
        random.seed(brand_seed)

    height = segment_height or (860 if orientation == "landscape" else 860)

    composition = _pick(TEXT_COMPOSITIONS)
    fonts = _pick(FONT_SYSTEMS)
    colors = _pick(TEXT_COLORS)
    boxes = _layout_boxes(composition, canvas_width, height)

    align = str(boxes["align"]["value"])
    hook_size = _headline_size(canvas_width, orientation)
    sub_size = _subheading_size(canvas_width, orientation)

    panel = boxes["panel"]
    eyebrow = boxes["eyebrow"]
    hook = boxes["hook"]
    subheading = boxes["subheading"]

    panel_x = int(panel["x"])
    panel_y = int(panel["y"])
    panel_w = int(panel["width"])
    panel_h = int(panel["height"])

    shapes: List[Dict[str, Any]] = [
        {
            "id": _shape_id("readability-panel"),
            "type": "rounded-rect",
            "x": _clamp(panel_x, 0, canvas_width - 10),
            "y": _clamp(panel_y, 0, height - 10),
            "width": _clamp(panel_w, 80, canvas_width),
            "height": _clamp(panel_h, 80, height),
            "backgroundColor": colors["panel"],
            "borderColor": colors["border"],
            "borderWidth": random.choice([0, 1]),
            "borderRadius": random.choice([0, 28, 42, 56]),
            "zIndex": 2,
            "opacity": random.choice([0.72, 0.82, 0.9]),
        },
        {
            "id": _shape_id("accent-line"),
            "type": "rectangle",
            "x": _clamp(int(eyebrow["x"]), 0, canvas_width - 10),
            "y": _clamp(int(eyebrow["y"]) - 18, 0, height - 10),
            "width": random.choice([
                72,
                110,
                160,
                int(int(eyebrow["width"]) * 0.42),
            ]),
            "height": random.choice([3, 4, 6]),
            "backgroundColor": "__BRAND_ACCENT__",
            "zIndex": 20,
            "opacity": random.choice([0.78, 0.9, 1]),
        },
        {
            "id": _shape_id("eyebrow"),
            "type": "text",
            "x": _clamp(int(eyebrow["x"]), 0, canvas_width - 10),
            "y": _clamp(int(eyebrow["y"]), 0, height - 10),
            "width": _clamp(int(eyebrow["width"]), 160, canvas_width),
            "height": _clamp(int(eyebrow["height"]), 36, 80),
            "zIndex": 21,
            "opacity": 1,
            "dataField": "subheading",
            "text": "",
            "customText": None,
            "fontSize": random.choice([22, 24, 26, 28]),
            "fontFamily": fonts["body_font"],
            "fontWeight": random.choice([500, 600, 700]),
            "textColor": "__BRAND_ACCENT__",
            "textAlign": align,
            "lineHeight": 1,
            "letterSpacing": random.choice([2.5, 3.5, 4.5]),
            "padding": 8,
            "backgroundColor": "transparent",
            "borderColor": "transparent",
            "borderWidth": 0,
        },
        {
            "id": _shape_id("hook"),
            "type": "text",
            "x": _clamp(int(hook["x"]), 0, canvas_width - 10),
            "y": _clamp(int(hook["y"]), 0, height - 10),
            "width": _clamp(int(hook["width"]), 420, canvas_width),
            "height": _clamp(int(hook["height"]), 130, height),
            "zIndex": 22,
            "opacity": 1,
            "dataField": "hook",
            "text": "",
            "customText": None,
            "fontSize": hook_size,
            "fontFamily": fonts["headline_font"],
            "fontWeight": fonts["headline_weight"],
            "textColor": colors["main"],
            "textAlign": align,
            "lineHeight": random.choice([0.86, 0.9, 0.94, 1.0]),
            "letterSpacing": fonts["headline_tracking"],
            "padding": 8,
            "backgroundColor": "transparent",
            "borderColor": "transparent",
            "borderWidth": 0,
            "shadowBlur": random.choice([0, 12, 18]),
            "shadowColor": "rgba(0,0,0,0.5)",
            "shadowX": 0,
            "shadowY": 6,
        },
        {
            "id": _shape_id("subheading"),
            "type": "text",
            "x": _clamp(int(subheading["x"]), 0, canvas_width - 10),
            "y": _clamp(int(subheading["y"]), 0, height - 10),
            "width": _clamp(int(subheading["width"]), 360, canvas_width),
            "height": _clamp(int(subheading["height"]), 64, 140),
            "zIndex": 23,
            "opacity": 1,
            "dataField": "subheading",
            "text": "",
            "customText": None,
            "fontSize": sub_size,
            "fontFamily": fonts["body_font"],
            "fontWeight": fonts["body_weight"],
            "textColor": colors["soft"],
            "textAlign": align,
            "lineHeight": random.choice([1.18, 1.24, 1.32]),
            "letterSpacing": random.choice([-0.2, 0, 0.2]),
            "padding": 8,
            "backgroundColor": "transparent",
            "borderColor": "transparent",
            "borderWidth": 0,
        },
        {
            "id": _shape_id("small-proof-line"),
            "type": "rectangle",
            "x": _clamp(panel_x + random.choice([18, 32, 48]), 0, canvas_width - 10),
            "y": _clamp(panel_y + panel_h - random.choice([28, 42, 58]), 0, height - 10),
            "width": random.choice([120, 180, 240]),
            "height": 2,
            "backgroundColor": colors["muted"],
            "zIndex": 20,
            "opacity": random.choice([0.45, 0.62, 0.8]),
        },
    ]

    return {
        "name": "Premium Hero Text Layer",
        "description": f"Premium hero text section using {composition}",
        "segment_type": "hero_image",
        "internal_segment_type": "hero_image",
        "segment_height": height,
        "canvas_width": canvas_width,
        "orientation": orientation,
        "composition_style": composition,
        "font_system": fonts["name"],
        "shapes": shapes,
    }