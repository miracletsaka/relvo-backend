from __future__ import annotations

import random
from typing import Any, Dict, List


COLOR_SYSTEMS: List[Dict[str, str]] = [
    {
        "name": "mega_sale_red_black",
        "bg": "#050505",
        "panel": "#111111",
        "panel2": "#1A0A0A",
        "accent": "#EF233C",
        "accent2": "#FFFFFF",
        "muted": "rgba(255,255,255,0.58)",
        "soft": "rgba(255,255,255,0.78)",
        "line": "rgba(255,255,255,0.14)",
    },
    {
        "name": "luxury_gold_black",
        "bg": "#060606",
        "panel": "#11100C",
        "panel2": "#1C1608",
        "accent": "#F5B84B",
        "accent2": "#FFFFFF",
        "muted": "rgba(255,255,255,0.55)",
        "soft": "rgba(255,255,255,0.76)",
        "line": "rgba(245,184,75,0.28)",
    },
    {
        "name": "electric_blue_dark",
        "bg": "#050816",
        "panel": "#0B1020",
        "panel2": "#071A35",
        "accent": "#2563EB",
        "accent2": "#FFFFFF",
        "muted": "rgba(255,255,255,0.55)",
        "soft": "rgba(255,255,255,0.78)",
        "line": "rgba(37,99,235,0.32)",
    },
    {
        "name": "purple_campaign",
        "bg": "#08030F",
        "panel": "#120A1F",
        "panel2": "#21112F",
        "accent": "#A855F7",
        "accent2": "#FFFFFF",
        "muted": "rgba(255,255,255,0.54)",
        "soft": "rgba(255,255,255,0.78)",
        "line": "rgba(168,85,247,0.32)",
    },
    {
        "name": "clean_white_red",
        "bg": "#F8FAFC",
        "panel": "#FFFFFF",
        "panel2": "#F1F5F9",
        "accent": "#E11D48",
        "accent2": "#09090B",
        "muted": "rgba(15,23,42,0.58)",
        "soft": "rgba(15,23,42,0.78)",
        "line": "rgba(15,23,42,0.12)",
    },
    {
        "name": "orange_commercial",
        "bg": "#120807",
        "panel": "#1C0E0B",
        "panel2": "#30140D",
        "accent": "#F97316",
        "accent2": "#FFFFFF",
        "muted": "rgba(255,255,255,0.56)",
        "soft": "rgba(255,255,255,0.78)",
        "line": "rgba(249,115,22,0.28)",
    },
]


COMPOSITIONS: List[str] = [
    "mega_sale_poster",
    "split_offer_card",
    "price_dominant_campaign",
    "diagonal_discount_ribbon",
    "luxury_offer_panel",
    "floating_badge_offer",
    "editorial_offer_block",
    "stacked_commercial_offer",
    "minimal_premium_offer",
]


FONT_SYSTEMS: List[Dict[str, Any]] = [
    {
        "name": "bebas_syne_campaign",
        "display": "Bebas Neue",
        "body": "Syne",
        "display_weight": 700,
        "body_weight": 400,
    },
    {
        "name": "syne_saas_bold",
        "display": "Syne",
        "body": "Syne",
        "display_weight": 800,
        "body_weight": 400,
    },
    {
        "name": "bebas_commercial",
        "display": "Bebas Neue",
        "body": "Syne",
        "display_weight": 700,
        "body_weight": 500,
    },
]


def _pick(items: List[Any]) -> Any:
    return random.choice(items)


def _shape_id(prefix: str) -> str:
    return f"offer-{prefix}-{random.randint(1000, 9999)}"


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def _layout(
    composition: str,
    canvas_width: int,
    height: int,
) -> Dict[str, Dict[str, int | str]]:
    left_x = int(canvas_width * 0.06)
    right_x = int(canvas_width * 0.55)
    center_x = int(canvas_width * 0.5)

    if composition == "mega_sale_poster":
        return {
            "align": {"value": "left"},
            "offer_title": {
                "x": left_x,
                "y": int(height * 0.18),
                "width": int(canvas_width * 0.48),
                "height": int(height * 0.18),
            },
            "offer_description": {
                "x": left_x,
                "y": int(height * 0.4),
                "width": int(canvas_width * 0.42),
                "height": int(height * 0.12),
            },
            "discount_label": {
                "x": left_x,
                "y": int(height * 0.1),
                "width": int(canvas_width * 0.28),
                "height": 54,
            },
            "price": {
                "x": right_x,
                "y": int(height * 0.22),
                "width": int(canvas_width * 0.34),
                "height": int(height * 0.2),
            },
            "compare_at_price": {
                "x": right_x + int(canvas_width * 0.02),
                "y": int(height * 0.48),
                "width": int(canvas_width * 0.22),
                "height": 58,
            },
        }

    if composition == "price_dominant_campaign":
        return {
            "align": {"value": "left"},
            "offer_title": {
                "x": left_x,
                "y": int(height * 0.14),
                "width": int(canvas_width * 0.38),
                "height": int(height * 0.16),
            },
            "offer_description": {
                "x": left_x,
                "y": int(height * 0.34),
                "width": int(canvas_width * 0.36),
                "height": int(height * 0.12),
            },
            "discount_label": {
                "x": int(canvas_width * 0.68),
                "y": int(height * 0.12),
                "width": int(canvas_width * 0.18),
                "height": 64,
            },
            "price": {
                "x": int(canvas_width * 0.46),
                "y": int(height * 0.26),
                "width": int(canvas_width * 0.44),
                "height": int(height * 0.26),
            },
            "compare_at_price": {
                "x": int(canvas_width * 0.5),
                "y": int(height * 0.56),
                "width": int(canvas_width * 0.22),
                "height": 60,
            },
        }

    if composition == "diagonal_discount_ribbon":
        return {
            "align": {"value": "left"},
            "offer_title": {
                "x": int(canvas_width * 0.1),
                "y": int(height * 0.18),
                "width": int(canvas_width * 0.44),
                "height": int(height * 0.18),
            },
            "offer_description": {
                "x": int(canvas_width * 0.1),
                "y": int(height * 0.43),
                "width": int(canvas_width * 0.38),
                "height": int(height * 0.12),
            },
            "discount_label": {
                "x": int(canvas_width * 0.62),
                "y": int(height * 0.12),
                "width": int(canvas_width * 0.26),
                "height": 70,
            },
            "price": {
                "x": int(canvas_width * 0.58),
                "y": int(height * 0.34),
                "width": int(canvas_width * 0.32),
                "height": int(height * 0.18),
            },
            "compare_at_price": {
                "x": int(canvas_width * 0.61),
                "y": int(height * 0.56),
                "width": int(canvas_width * 0.2),
                "height": 56,
            },
        }

    if composition == "luxury_offer_panel":
        return {
            "align": {"value": "center"},
            "offer_title": {
                "x": int(canvas_width * 0.2),
                "y": int(height * 0.18),
                "width": int(canvas_width * 0.6),
                "height": int(height * 0.14),
            },
            "offer_description": {
                "x": int(canvas_width * 0.26),
                "y": int(height * 0.36),
                "width": int(canvas_width * 0.48),
                "height": int(height * 0.12),
            },
            "discount_label": {
                "x": int(canvas_width * 0.36),
                "y": int(height * 0.1),
                "width": int(canvas_width * 0.28),
                "height": 54,
            },
            "price": {
                "x": int(canvas_width * 0.33),
                "y": int(height * 0.52),
                "width": int(canvas_width * 0.34),
                "height": int(height * 0.17),
            },
            "compare_at_price": {
                "x": int(canvas_width * 0.39),
                "y": int(height * 0.72),
                "width": int(canvas_width * 0.22),
                "height": 52,
            },
        }

    if composition == "minimal_premium_offer":
        return {
            "align": {"value": "left"},
            "offer_title": {
                "x": int(canvas_width * 0.12),
                "y": int(height * 0.18),
                "width": int(canvas_width * 0.46),
                "height": int(height * 0.16),
            },
            "offer_description": {
                "x": int(canvas_width * 0.12),
                "y": int(height * 0.39),
                "width": int(canvas_width * 0.38),
                "height": int(height * 0.1),
            },
            "discount_label": {
                "x": int(canvas_width * 0.12),
                "y": int(height * 0.1),
                "width": int(canvas_width * 0.22),
                "height": 48,
            },
            "price": {
                "x": int(canvas_width * 0.64),
                "y": int(height * 0.22),
                "width": int(canvas_width * 0.24),
                "height": int(height * 0.16),
            },
            "compare_at_price": {
                "x": int(canvas_width * 0.65),
                "y": int(height * 0.42),
                "width": int(canvas_width * 0.18),
                "height": 50,
            },
        }

    return {
        "align": {"value": "left"},
        "offer_title": {
            "x": left_x,
            "y": int(height * 0.16),
            "width": int(canvas_width * 0.46),
            "height": int(height * 0.17),
        },
        "offer_description": {
            "x": left_x,
            "y": int(height * 0.38),
            "width": int(canvas_width * 0.4),
            "height": int(height * 0.12),
        },
        "discount_label": {
            "x": left_x,
            "y": int(height * 0.09),
            "width": int(canvas_width * 0.24),
            "height": 54,
        },
        "price": {
            "x": center_x,
            "y": int(height * 0.28),
            "width": int(canvas_width * 0.34),
            "height": int(height * 0.18),
        },
        "compare_at_price": {
            "x": center_x + int(canvas_width * 0.02),
            "y": int(height * 0.5),
            "width": int(canvas_width * 0.2),
            "height": 54,
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

    height = segment_height or (760 if orientation == "landscape" else 860)

    color = _pick(COLOR_SYSTEMS)
    composition = _pick(COMPOSITIONS)
    fonts = _pick(FONT_SYSTEMS)
    layout = _layout(composition, canvas_width, height)

    align = str(layout["align"]["value"])

    bg = color["bg"]
    panel = color["panel"]
    panel2 = color["panel2"]
    accent = color["accent"]
    accent2 = color["accent2"]
    muted = color["muted"]
    soft = color["soft"]
    line = color["line"]

    title = layout["offer_title"]
    description = layout["offer_description"]
    discount = layout["discount_label"]
    price = layout["price"]
    compare = layout["compare_at_price"]

    shapes: List[Dict[str, Any]] = [
        {
            "id": _shape_id("background"),
            "type": "rounded-rect",
            "x": 0,
            "y": 0,
            "width": canvas_width,
            "height": height,
            "backgroundColor": bg,
            "borderRadius": 0,
            "zIndex": 0,
            "opacity": 1,
        },
        {
            "id": _shape_id("main-panel"),
            "type": "rounded-rect",
            "x": random.choice([48, 72, 96, int(canvas_width * 0.06)]),
            "y": random.choice([48, 64, 82]),
            "width": random.choice([
                int(canvas_width * 0.58),
                int(canvas_width * 0.66),
                int(canvas_width * 0.74),
                int(canvas_width * 0.86),
            ]),
            "height": random.choice([
                int(height * 0.68),
                int(height * 0.76),
                int(height * 0.84),
            ]),
            "backgroundColor": panel,
            "borderColor": line,
            "borderWidth": random.choice([1, 2]),
            "borderRadius": random.choice([24, 36, 48, 60]),
            "zIndex": 1,
            "opacity": random.choice([0.82, 0.9, 0.96]),
        },
        {
            "id": _shape_id("secondary-panel"),
            "type": "rounded-rect",
            "x": random.choice([
                int(canvas_width * 0.48),
                int(canvas_width * 0.56),
                int(canvas_width * 0.62),
            ]),
            "y": random.choice([
                int(height * 0.12),
                int(height * 0.18),
                int(height * 0.24),
            ]),
            "width": random.choice([
                int(canvas_width * 0.26),
                int(canvas_width * 0.32),
                int(canvas_width * 0.38),
            ]),
            "height": random.choice([
                int(height * 0.38),
                int(height * 0.48),
                int(height * 0.58),
            ]),
            "backgroundColor": panel2,
            "borderColor": line,
            "borderWidth": 1,
            "borderRadius": random.choice([28, 42, 56]),
            "zIndex": 2,
            "opacity": random.choice([0.58, 0.68, 0.78]),
        },
        {
            "id": _shape_id("large-glow"),
            "type": "circle",
            "x": random.choice([
                -int(canvas_width * 0.12),
                int(canvas_width * 0.54),
                int(canvas_width * 0.7),
            ]),
            "y": random.choice([
                -int(height * 0.24),
                int(height * 0.36),
                int(height * 0.56),
            ]),
            "width": random.choice([
                int(canvas_width * 0.24),
                int(canvas_width * 0.34),
                int(canvas_width * 0.42),
            ]),
            "height": random.choice([
                int(canvas_width * 0.24),
                int(canvas_width * 0.34),
                int(canvas_width * 0.42),
            ]),
            "backgroundColor": accent,
            "borderRadius": 999,
            "zIndex": 2,
            "opacity": random.choice([0.12, 0.16, 0.22]),
        },
        {
            "id": _shape_id("sale-ribbon"),
            "type": "rectangle",
            "x": random.choice([
                0,
                int(canvas_width * 0.04),
                int(canvas_width * 0.64),
            ]),
            "y": random.choice([
                int(height * 0.06),
                int(height * 0.16),
                int(height * 0.78),
            ]),
            "width": random.choice([
                int(canvas_width * 0.22),
                int(canvas_width * 0.34),
                int(canvas_width * 0.46),
            ]),
            "height": random.choice([10, 16, 24, 42]),
            "backgroundColor": accent,
            "zIndex": 3,
            "opacity": random.choice([0.76, 0.88, 1]),
            "rotation": random.choice([0, 0, 0, -5, 5]),
        },
        {
            "id": _shape_id("badge-circle"),
            "type": "circle",
            "x": random.choice([
                int(canvas_width * 0.68),
                int(canvas_width * 0.78),
                int(canvas_width * 0.84),
            ]),
            "y": random.choice([
                int(height * 0.12),
                int(height * 0.2),
                int(height * 0.34),
            ]),
            "width": random.choice([120, 150, 180, 220]),
            "height": random.choice([120, 150, 180, 220]),
            "backgroundColor": accent,
            "borderColor": accent2,
            "borderWidth": random.choice([0, 4, 6]),
            "borderRadius": 999,
            "zIndex": 4,
            "opacity": random.choice([0.86, 0.94, 1]),
        },
        {
            "id": _shape_id("discount-label"),
            "type": "text",
            "x": _clamp(int(discount["x"]), 0, canvas_width - 10),
            "y": _clamp(int(discount["y"]), 0, height - 10),
            "width": _clamp(int(discount["width"]), 180, canvas_width),
            "height": _clamp(int(discount["height"]), 44, 90),
            "zIndex": 20,
            "opacity": 1,
            "dataField": "discount_label",
            "text": "",
            "customText": None,
            "fontSize": random.choice([24, 28, 32, 36]),
            "fontFamily": fonts["body"],
            "fontWeight": random.choice([600, 700, 800]),
            "textColor": accent,
            "textAlign": align,
            "lineHeight": 1,
            "letterSpacing": random.choice([1.5, 2.5, 3.5]),
            "padding": 8,
            "backgroundColor": "transparent",
            "borderColor": "transparent",
            "borderWidth": 0,
        },
        {
            "id": _shape_id("offer-title"),
            "type": "text",
            "x": _clamp(int(title["x"]), 0, canvas_width - 10),
            "y": _clamp(int(title["y"]), 0, height - 10),
            "width": _clamp(int(title["width"]), 420, canvas_width),
            "height": _clamp(int(title["height"]), 110, height),
            "zIndex": 21,
            "opacity": 1,
            "dataField": "offer_title",
            "text": "",
            "customText": None,
            "fontSize": random.choice([72, 84, 96, 108, 124]),
            "fontFamily": fonts["display"],
            "fontWeight": fonts["display_weight"],
            "textColor": accent2,
            "textAlign": align,
            "lineHeight": random.choice([0.86, 0.92, 1.0]),
            "letterSpacing": random.choice([-1.5, -0.5, 0, 0.5]),
            "padding": 8,
            "backgroundColor": "transparent",
            "borderColor": "transparent",
            "borderWidth": 0,
            "shadowBlur": random.choice([0, 10, 18]),
            "shadowColor": "rgba(0,0,0,0.45)",
            "shadowX": 0,
            "shadowY": 6,
        },
        {
            "id": _shape_id("offer-description"),
            "type": "text",
            "x": _clamp(int(description["x"]), 0, canvas_width - 10),
            "y": _clamp(int(description["y"]), 0, height - 10),
            "width": _clamp(int(description["width"]), 360, canvas_width),
            "height": _clamp(int(description["height"]), 70, 150),
            "zIndex": 22,
            "opacity": 1,
            "dataField": "offer_description",
            "text": "",
            "customText": None,
            "fontSize": random.choice([26, 30, 34, 38]),
            "fontFamily": fonts["body"],
            "fontWeight": fonts["body_weight"],
            "textColor": soft,
            "textAlign": align,
            "lineHeight": random.choice([1.18, 1.24, 1.32]),
            "letterSpacing": random.choice([-0.2, 0, 0.2]),
            "padding": 8,
            "backgroundColor": "transparent",
            "borderColor": "transparent",
            "borderWidth": 0,
        },
        {
            "id": _shape_id("price"),
            "type": "text",
            "x": _clamp(int(price["x"]), 0, canvas_width - 10),
            "y": _clamp(int(price["y"]), 0, height - 10),
            "width": _clamp(int(price["width"]), 260, canvas_width),
            "height": _clamp(int(price["height"]), 100, height),
            "zIndex": 23,
            "opacity": 1,
            "dataField": "price",
            "text": "",
            "customText": None,
            "fontSize": random.choice([92, 108, 124, 142, 160]),
            "fontFamily": fonts["display"],
            "fontWeight": fonts["display_weight"],
            "textColor": accent,
            "textAlign": random.choice([align, "center"]),
            "lineHeight": 0.9,
            "letterSpacing": random.choice([-2, -1, 0]),
            "padding": 8,
            "backgroundColor": "transparent",
            "borderColor": "transparent",
            "borderWidth": 0,
            "shadowBlur": random.choice([0, 14, 24]),
            "shadowColor": "rgba(0,0,0,0.55)",
            "shadowX": 0,
            "shadowY": 8,
        },
        {
            "id": _shape_id("compare-at-price"),
            "type": "text",
            "x": _clamp(int(compare["x"]), 0, canvas_width - 10),
            "y": _clamp(int(compare["y"]), 0, height - 10),
            "width": _clamp(int(compare["width"]), 180, canvas_width),
            "height": _clamp(int(compare["height"]), 44, 90),
            "zIndex": 24,
            "opacity": 1,
            "dataField": "compare_at_price",
            "text": "",
            "customText": None,
            "fontSize": random.choice([26, 30, 34, 38]),
            "fontFamily": fonts["body"],
            "fontWeight": random.choice([500, 600, 700]),
            "textColor": muted,
            "textAlign": random.choice([align, "center"]),
            "lineHeight": 1,
            "letterSpacing": 0,
            "padding": 8,
            "backgroundColor": "transparent",
            "borderColor": "transparent",
            "borderWidth": 0,
        },
        {
            "id": _shape_id("strike-line"),
            "type": "rectangle",
            "x": _clamp(int(compare["x"]) + 10, 0, canvas_width - 10),
            "y": _clamp(int(compare["y"]) + int(compare["height"]) // 2, 0, height - 10),
            "width": _clamp(int(int(compare["width"]) * 0.72), 80, canvas_width),
            "height": 3,
            "backgroundColor": accent,
            "zIndex": 25,
            "opacity": random.choice([0.7, 0.86, 1]),
        },
    ]

    return {
        "name": "Premium Offer Block",
        "description": f"Premium commercial offer layout using {composition}",
        "segment_type": "offer_block",
        "internal_segment_type": "offer_block",
        "segment_height": height,
        "canvas_width": canvas_width,
        "orientation": orientation,
        "composition_style": composition,
        "color_system": color["name"],
        "font_system": fonts["name"],
        "shapes": shapes,
    }