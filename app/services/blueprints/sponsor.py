# backend/app/services/blueprints/sponsor.py

from typing import Dict
from .shared import PAD, A, DK, WHT, txt, rect, circle, package_blueprint

SEGMENT_TYPE = "sponsor_bar"
HEIGHT = 180

VARIANTS = [
    [
        rect("sponsor-bg-a", 0, 0, 1080, HEIGHT, DK, z=0),
        circle("sponsor-glow-a", 760, -140, 380, A, z=1, op=0.12),
        txt("sponsor-main-a", "proof", PAD, 44, 760, 110, 52, "Bebas Neue", 900, WHT, "left", 0.92, -1, z=10),
        rect("sponsor-rule-a", PAD, 172, 120, 5, A, 999, z=8),
    ],
    [
        rect("sponsor-bg-b", 0, 0, 1080, HEIGHT, "#000000", z=0),
        rect("sponsor-top-b", PAD, 0, 968, 3, A, z=2),
        txt("sponsor-main-b", "proof", PAD, 50, 968, 100, 46, "Syne", 800, WHT, "center", 1.05, -0.5, z=10),
    ],
]

def get(seed: int = 0, brand_seed: int | None = None, **kwargs) -> Dict:
    return package_blueprint(SEGMENT_TYPE, HEIGHT, VARIANTS, seed)
