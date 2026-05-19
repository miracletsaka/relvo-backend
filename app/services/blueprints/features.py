# backend/app/services/blueprints/features.py

from typing import Dict
from .shared import PAD, A, DK, WHT, txt, rect, circle, package_blueprint

SEGMENT_TYPE = "feature_list"
HEIGHT = 340

VARIANTS = [
    [
        rect("features-bg-a", 0, 0, 1080, HEIGHT, DK, z=0),
        circle("features-glow-a", 760, -140, 380, A, z=1, op=0.12),
        txt("features-main-a", "headline", PAD, 44, 760, 110, 52, "Bebas Neue", 900, WHT, "left", 0.92, -1, z=10),
        rect("features-rule-a", PAD, 172, 120, 5, A, 999, z=8),
    ],
    [
        rect("features-bg-b", 0, 0, 1080, HEIGHT, "#000000", z=0),
        rect("features-top-b", PAD, 0, 968, 3, A, z=2),
        txt("features-main-b", "headline", PAD, 50, 968, 100, 46, "Syne", 800, WHT, "center", 1.05, -0.5, z=10),
    ],
]

def get(seed: int = 0, brand_seed: int | None = None, **kwargs) -> Dict:
    return package_blueprint(SEGMENT_TYPE, HEIGHT, VARIANTS, seed)
