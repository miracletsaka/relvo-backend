from __future__ import annotations

import random
from typing import Any, Dict, List


COLOR_SYSTEMS: List[Dict[str, str]] = [
    {
        "name": "red_black_white",
        "bg": "#050505",
        "panel": "#111111",
        "accent": "#EF233C",
        "accent2": "#FFFFFF",
        "muted": "#2B2B2B",
    },
    {
        "name": "luxury_black_gold",
        "bg": "#060606",
        "panel": "#11100C",
        "accent": "#F5B84B",
        "accent2": "#FFFFFF",
        "muted": "#2A2415",
    },
    {
        "name": "deep_blue_electric",
        "bg": "#050816",
        "panel": "#0B1020",
        "accent": "#2563EB",
        "accent2": "#FFFFFF",
        "muted": "#111827",
    },
    {
        "name": "purple_neon_black",
        "bg": "#08030F",
        "panel": "#120A1F",
        "accent": "#A855F7",
        "accent2": "#FFFFFF",
        "muted": "#21112F",
    },
    {
        "name": "orange_commercial",
        "bg": "#120807",
        "panel": "#1C0E0B",
        "accent": "#F97316",
        "accent2": "#FFFFFF",
        "muted": "#30140D",
    },
    {
        "name": "emerald_dark",
        "bg": "#03130F",
        "panel": "#071D17",
        "accent": "#14B8A6",
        "accent2": "#FFFFFF",
        "muted": "#0B2A22",
    },
]


COMPOSITIONS: List[str] = [
    "bold_ad_card",
    "diagonal_sale_energy",
    "split_commercial_panel",
    "full_bleed_poster_media",
    "floating_product_frame",
    "premium_dark_campaign",
    "layered_social_poster",
    "editorial_marketing_card",
]


def _pick(items: List[Any]) -> Any:
    return random.choice(items)


def _shape_id(prefix: str) -> str:
    return f"hero-media-{prefix}-{random.randint(1000, 9999)}"


def get(
    brand_seed: int | None = None,
    canvas_width: int = 1920,
    orientation: str = "landscape",
    segment_height: int | None = None,
) -> Dict[str, Any]:
    if brand_seed is not None:
        random.seed(brand_seed)

    height = segment_height or (1080 if orientation == "landscape" else 1080)

    color = _pick(COLOR_SYSTEMS)
    composition = _pick(COMPOSITIONS)

    bg = color["bg"]
    panel = color["panel"]
    accent = color["accent"]
    accent2 = color["accent2"]
    muted = color["muted"]

    image_x = random.choice([
        int(canvas_width * 0.46),
        int(canvas_width * 0.52),
        int(canvas_width * 0.58),
        int(canvas_width * 0.08),
    ])

    image_y = random.choice([
        int(height * 0.08),
        int(height * 0.12),
        int(height * 0.18),
    ])

    image_w = random.choice([
        int(canvas_width * 0.34),
        int(canvas_width * 0.42),
        int(canvas_width * 0.5),
        int(canvas_width * 0.62),
    ])

    image_h = random.choice([
        int(height * 0.58),
        int(height * 0.68),
        int(height * 0.78),
        int(height * 0.9),
    ])

    image_x = max(0, min(image_x, canvas_width - image_w - 16))
    image_y = max(0, min(image_y, height - image_h - 16))

    shapes: List[Dict[str, Any]] = [
        {
            "id": _shape_id("bg"),
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
            "id": _shape_id("panel-left"),
            "type": "rounded-rect",
            "x": random.choice([0, 64, 96]),
            "y": random.choice([0, 64, 96]),
            "width": random.choice([
                int(canvas_width * 0.34),
                int(canvas_width * 0.42),
                int(canvas_width * 0.48),
            ]),
            "height": random.choice([
                int(height * 0.72),
                int(height * 0.84),
                height,
            ]),
            "backgroundColor": panel,
            "borderRadius": random.choice([0, 28, 42, 56]),
            "borderColor": "rgba(255,255,255,0.08)",
            "borderWidth": 1,
            "zIndex": 1,
            "opacity": random.choice([0.78, 0.86, 0.92]),
        },
        {
            "id": _shape_id("accent-band"),
            "type": "rectangle",
            "x": random.choice([0, int(canvas_width * 0.06), int(canvas_width * 0.72)]),
            "y": random.choice([0, int(height * 0.08), int(height * 0.78)]),
            "width": random.choice([
                int(canvas_width * 0.18),
                int(canvas_width * 0.28),
                int(canvas_width * 0.42),
                canvas_width,
            ]),
            "height": random.choice([8, 14, 22, int(height * 0.12)]),
            "backgroundColor": accent,
            "zIndex": 2,
            "opacity": random.choice([0.65, 0.78, 0.9]),
        },
        {
            "id": _shape_id("big-orb"),
            "type": "circle",
            "x": random.choice([
                -int(canvas_width * 0.12),
                int(canvas_width * 0.62),
                int(canvas_width * 0.72),
            ]),
            "y": random.choice([
                -int(height * 0.18),
                int(height * 0.44),
                int(height * 0.62),
            ]),
            "width": random.choice([
                int(canvas_width * 0.26),
                int(canvas_width * 0.36),
                int(canvas_width * 0.48),
            ]),
            "height": random.choice([
                int(canvas_width * 0.26),
                int(canvas_width * 0.36),
                int(canvas_width * 0.48),
            ]),
            "backgroundColor": accent,
            "borderRadius": 999,
            "zIndex": 2,
            "opacity": random.choice([0.14, 0.18, 0.24]),
        },
        {
            "id": _shape_id("small-orb"),
            "type": "circle",
            "x": random.choice([
                int(canvas_width * 0.06),
                int(canvas_width * 0.22),
                int(canvas_width * 0.82),
            ]),
            "y": random.choice([
                int(height * 0.08),
                int(height * 0.66),
                int(height * 0.78),
            ]),
            "width": random.choice([120, 180, 260, 340]),
            "height": random.choice([120, 180, 260, 340]),
            "backgroundColor": muted,
            "borderRadius": 999,
            "zIndex": 2,
            "opacity": random.choice([0.35, 0.45, 0.55]),
        },
        {
            "id": _shape_id("image-frame"),
            "type": "rounded-rect",
            "x": image_x - 18,
            "y": image_y - 18,
            "width": image_w + 36,
            "height": image_h + 36,
            "backgroundColor": "rgba(255,255,255,0.06)",
            "borderColor": random.choice([
                "rgba(255,255,255,0.18)",
                accent,
                "rgba(255,255,255,0.10)",
            ]),
            "borderWidth": random.choice([1, 2]),
            "borderRadius": random.choice([26, 36, 48]),
            "zIndex": 4,
            "opacity": 1,
        },
        {
            "id": _shape_id("image"),
            "type": "image",
            "x": image_x,
            "y": image_y,
            "width": image_w,
            "height": image_h,
            "src": None,
            "slotKey": "hero_person",
            "slotLabel": "Hero Image",
            "slotType": "image",
            "slotRole": "hero",
            "fit": "cover",
            "radius": random.choice([18, 28, 36, 44]),
            "zIndex": 5,
            "opacity": random.choice([0.9, 0.94, 1]),
        },
        {
            "id": _shape_id("image-scrim"),
            "type": "gradient-overlay",
            "x": image_x,
            "y": image_y,
            "width": image_w,
            "height": image_h,
            "gradientColors": [
                {"stop": 0, "color": "rgba(0,0,0,0.04)"},
                {"stop": 1, "color": "rgba(0,0,0,0.5)"},
            ],
            "gradientAngle": random.choice([90, 135, 180, 225]),
            "backgroundColor": "transparent",
            "zIndex": 6,
            "opacity": 1,
        },
        {
            "id": _shape_id("light-sweep"),
            "type": "gradient-overlay",
            "x": random.choice([0, int(canvas_width * 0.18), int(canvas_width * 0.42)]),
            "y": random.choice([0, int(height * 0.12), int(height * 0.28)]),
            "width": random.choice([
                int(canvas_width * 0.46),
                int(canvas_width * 0.62),
                canvas_width,
            ]),
            "height": random.choice([
                int(height * 0.18),
                int(height * 0.28),
                int(height * 0.42),
            ]),
            "gradientColors": [
                {"stop": 0, "color": "rgba(255,255,255,0.0)"},
                {"stop": 0.5, "color": "rgba(255,255,255,0.10)"},
                {"stop": 1, "color": "rgba(255,255,255,0.0)"},
            ],
            "gradientAngle": random.choice([25, 35, 145]),
            "backgroundColor": "transparent",
            "zIndex": 7,
            "opacity": random.choice([0.45, 0.62, 0.8]),
        },
        {
            "id": _shape_id("badge-dot"),
            "type": "circle",
            "x": random.choice([
                image_x - 32,
                image_x + image_w - 64,
                int(canvas_width * 0.14),
            ]),
            "y": random.choice([
                image_y - 32,
                image_y + image_h - 80,
                int(height * 0.16),
            ]),
            "width": random.choice([70, 96, 120]),
            "height": random.choice([70, 96, 120]),
            "backgroundColor": accent2,
            "borderRadius": 999,
            "borderColor": accent,
            "borderWidth": random.choice([0, 4, 6]),
            "zIndex": 8,
            "opacity": random.choice([0.82, 0.92, 1]),
        },
    ]

    return {
        "name": "Hero Media AI Seed",
        "description": f"Premium decorative seed using {composition} / {color['name']}",
        "segment_type": "hero_media",
        "internal_segment_type": "hero_media",
        "segment_height": height,
        "canvas_width": canvas_width,
        "orientation": orientation,
        "composition_style": composition,
        "color_system": color["name"],
        "shapes": shapes,
    }