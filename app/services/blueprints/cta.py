# backend/app/services/blueprints/cta.py

from typing import Dict
from .shared import PAD, A, DK, WHT, txt, rect, circle, package_blueprint

SEGMENT_TYPE = "cta_button"
HEIGHT = 180

VARIANTS = [
    [
        rect("cta-bg-a", 0, 0, 1080, HEIGHT, DK, z=0),
        circle("cta-glow-a", 760, -140, 380, A, z=1, op=0.12),
        txt("cta-main-a", "cta_text", PAD, 44, 760, 110, 52, "Bebas Neue", 900, WHT, "left", 0.92, -1, z=10),
        rect("cta-rule-a", PAD, 172, 120, 5, A, 999, z=8),
    ],
    [
        rect("cta-bg-b", 0, 0, 1080, HEIGHT, "#000000", z=0),
        rect("cta-top-b", PAD, 0, 968, 3, A, z=2),
        txt("cta-main-b", "cta_text", PAD, 50, 968, 100, 46, "Syne", 800, WHT, "center", 1.05, -0.5, z=10),
    ],
]

def get(seed: int = 0, brand_seed: int | None = None, **kwargs) -> Dict:
    return package_blueprint(SEGMENT_TYPE, HEIGHT, VARIANTS, seed)
