# backend/app/services/hero_image_blueprints.py

import random
import time
from typing import Dict, List, Optional

CANVAS_WIDTH = 1080
HERO_HEIGHT = 430


def _img(
    id_: str,
    x: int,
    y: int,
    w: int,
    h: int,
    *,
    fit: str = "cover",
    r: int = 0,
    z: int = 1,
    opacity: float = 1.0,
    rotate: float = 0,
):
    return {
        "id": id_,
        "type": "image",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "slotKey": "hero_person",
        "slotLabel": "Hero Image",
        "slotType": "image",
        "slotRole": "hero",
        "fit": fit,
        "radius": r,
        "rotation": rotate,
        "slotVisibleWhenEmpty": False,
        "src": None,
        "zIndex": z,
        "opacity": opacity,
        "backgroundColor": "transparent",
        "borderColor": "transparent",
        "borderWidth": 0,
        "shadowBlur": 0,
        "shadowX": 0,
        "shadowY": 0,
        "shadowColor": "#000000",
    }


def _rect(id_: str, x: int, y: int, w: int, h: int, bg: str, *, r: int = 0, z: int = 2, opacity: float = 1.0):
    return {
        "id": id_,
        "type": "rounded-rect",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "backgroundColor": bg,
        "borderRadius": r,
        "zIndex": z,
        "opacity": opacity,
        "borderColor": "transparent",
        "borderWidth": 0,
        "shadowBlur": 0,
        "shadowX": 0,
        "shadowY": 0,
        "shadowColor": "#000000",
    }


def _grad(id_: str, x: int, y: int, w: int, h: int, stops: List[Dict], *, angle: int = 180, z: int = 2, opacity: float = 1.0):
    return {
        "id": id_,
        "type": "gradient-overlay",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "gradientColors": stops,
        "gradientAngle": angle,
        "backgroundColor": "transparent",
        "borderWidth": 0,
        "zIndex": z,
        "opacity": opacity,
    }


def _circle(id_: str, x: int, y: int, size: int, bg: str, *, z: int = 2, opacity: float = 1.0):
    return {
        "id": id_,
        "type": "circle",
        "x": x,
        "y": y,
        "width": size,
        "height": size,
        "backgroundColor": bg,
        "zIndex": z,
        "opacity": opacity,
        "borderColor": "transparent",
        "borderWidth": 0,
        "shadowBlur": 0,
        "shadowX": 0,
        "shadowY": 0,
        "shadowColor": "#000000",
    }


DARK_LEFT = [
    {"stop": 0, "color": "rgba(0,0,0,0.88)"},
    {"stop": 0.45, "color": "rgba(0,0,0,0.45)"},
    {"stop": 1, "color": "rgba(0,0,0,0.05)"},
]

DARK_RIGHT = [
    {"stop": 0, "color": "rgba(0,0,0,0.05)"},
    {"stop": 0.55, "color": "rgba(0,0,0,0.35)"},
    {"stop": 1, "color": "rgba(0,0,0,0.88)"},
]

DARK_BOTTOM = [
    {"stop": 0, "color": "rgba(0,0,0,0.04)"},
    {"stop": 1, "color": "rgba(0,0,0,0.88)"},
]

DARK_FULL = [
    {"stop": 0, "color": "rgba(0,0,0,0.40)"},
    {"stop": 1, "color": "rgba(0,0,0,0.72)"},
]


HERO_IMAGE_BLUEPRINTS: List[List[Dict]] = [
    # 1. Full bleed image behind all hero text, with dark overlays for readability.
    [
        _img("hi-full-image", 0, 0, 1080, 430, r=0, z=0),
        _grad("hi-full-left-scrim", 0, 0, 1080, 430, DARK_LEFT, angle=90, z=1, opacity=1),
        _grad("hi-full-bottom-scrim", 0, 180, 1080, 250, DARK_BOTTOM, angle=180, z=1, opacity=1),
    ],

    # 2. Right-side image panel. Text can sit left safely.
    [
        _rect("hi-right-bg", 0, 0, 1080, 430, "#05070b", z=0),
        _img("hi-right-image", 520, 0, 560, 430, r=0, z=1),
        _grad("hi-right-scrim", 420, 0, 240, 430, DARK_RIGHT, angle=90, z=2, opacity=0.95),
        _circle("hi-right-glow", 720, -120, 360, "__BRAND_ACCENT__", z=0, opacity=0.12),
    ],

    # 3. Left-side image panel. Text can sit right safely.
    [
        _rect("hi-left-bg", 0, 0, 1080, 430, "#05070b", z=0),
        _img("hi-left-image", 0, 0, 560, 430, r=0, z=1),
        _grad("hi-left-scrim", 420, 0, 260, 430, DARK_LEFT, angle=90, z=2, opacity=0.92),
        _circle("hi-left-glow", -140, 40, 380, "__BRAND_ACCENT__", z=0, opacity=0.12),
    ],

    # 4. Rounded editorial image card on the right.
    [
        _rect("hi-card-bg", 0, 0, 1080, 430, "#05070b", z=0),
        _circle("hi-card-glow", 660, 20, 420, "__BRAND_ACCENT__", z=0, opacity=0.10),
        _rect("hi-card-shadow", 548, 42, 472, 346, "rgba(0,0,0,0.45)", r=34, z=1, opacity=1),
        _img("hi-card-image", 540, 34, 472, 346, r=34, z=2),
        _grad("hi-card-soft", 520, 34, 180, 346, DARK_LEFT, angle=90, z=3, opacity=0.45),
    ],

    # 5. Rounded editorial image card on the left.
    [
        _rect("hi-card-left-bg", 0, 0, 1080, 430, "#05070b", z=0),
        _circle("hi-card-left-glow", -70, 20, 420, "__BRAND_ACCENT__", z=0, opacity=0.10),
        _rect("hi-card-left-shadow", 68, 42, 472, 346, "rgba(0,0,0,0.45)", r=34, z=1, opacity=1),
        _img("hi-card-left-image", 60, 34, 472, 346, r=34, z=2),
        _grad("hi-card-left-soft", 380, 34, 180, 346, DARK_RIGHT, angle=90, z=3, opacity=0.45),
    ],

    # 6. Wide top strip image, text can live bottom.
    [
        _rect("hi-top-bg", 0, 0, 1080, 430, "#05070b", z=0),
        _img("hi-top-image", 0, 0, 1080, 260, r=0, z=1),
        _grad("hi-top-fade", 0, 110, 1080, 200, DARK_BOTTOM, angle=180, z=2, opacity=1),
        _rect("hi-top-panel", 0, 260, 1080, 170, "rgba(5,7,11,0.96)", z=2, opacity=1),
    ],

    # 7. Bottom strip image, text can live top.
    [
        _rect("hi-bottom-bg", 0, 0, 1080, 430, "#05070b", z=0),
        _img("hi-bottom-image", 0, 190, 1080, 240, r=0, z=1),
        _grad("hi-bottom-fade", 0, 160, 1080, 140, DARK_FULL, angle=180, z=2, opacity=0.9),
        _rect("hi-bottom-panel", 0, 0, 1080, 210, "rgba(5,7,11,0.70)", z=1, opacity=1),
    ],

    # 8. Diagonal poster energy: image is oversized and offset.
    [
        _rect("hi-diagonal-bg", 0, 0, 1080, 430, "#05070b", z=0),
        _img("hi-diagonal-image", 430, -28, 690, 500, r=26, z=1, rotate=-4),
        _grad("hi-diagonal-scrim", 0, 0, 760, 430, DARK_LEFT, angle=90, z=2, opacity=1),
        _rect("hi-diagonal-accent", 0, 0, 10, 430, "__BRAND_ACCENT__", z=3, opacity=0.95),
    ],

    # 9. Circular crop hero image.
    [
        _rect("hi-circle-bg", 0, 0, 1080, 430, "#05070b", z=0),
        _circle("hi-circle-glow", 650, 0, 430, "__BRAND_ACCENT__", z=0, opacity=0.13),
        _img("hi-circle-image", 640, 36, 360, 360, r=999, z=2),
        _grad("hi-circle-scrim", 450, 0, 260, 430, DARK_LEFT, angle=90, z=3, opacity=0.55),
    ],

    # 10. Image as low-opacity watermark behind text.
    [
        _img("hi-watermark-image", 0, 0, 1080, 430, r=0, z=0, opacity=0.38),
        _rect("hi-watermark-dark", 0, 0, 1080, 430, "rgba(0,0,0,0.62)", z=1, opacity=1),
        _circle("hi-watermark-glow", 700, -140, 420, "__BRAND_ACCENT__", z=2, opacity=0.10),
    ],
]


def get_hero_image_blueprint(seed: Optional[int] = None) -> Dict:
    rng = random.Random(seed if seed is not None else time.time_ns())
    idx = rng.randrange(len(HERO_IMAGE_BLUEPRINTS))
    return {
        "segment_type": "hero_media",
        "segment_height": HERO_HEIGHT,
        "variant_index": idx,
        "shapes": HERO_IMAGE_BLUEPRINTS[idx],
    }
