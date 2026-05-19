# backend/app/services/blueprints/footer.py

from typing import Dict
from .shared import PAD, A, DK, BLK, txt, rect, package_blueprint

SEGMENT_TYPE = "footer"
HEIGHT = 190

VARIANTS = [
    [
        rect("footer-bg-a", 0, 0, 1080, HEIGHT, BLK, z=0),
        rect("footer-line-a", PAD, 0, 968, 3, A, z=2),
        txt("footer-row1-a", "contact_row1", PAD, 54, 650, 34, 20, "Syne", 600, "rgba(255,255,255,0.72)", "left", z=5),
        txt("footer-row2-a", "contact_row2", PAD, 98, 650, 30, 16, "Syne", 400, "rgba(255,255,255,0.45)", "left", z=5),
        txt("footer-web-a", "business_website", 760, 76, 264, 34, 20, "Syne", 700, A, "right", z=5),
    ],
    [
        rect("footer-bg-b", 0, 0, 1080, HEIGHT, DK, z=0),
        rect("footer-left-b", 0, 0, 6, HEIGHT, A, z=2),
        txt("footer-row1-b", "contact_row1", PAD + 18, 52, 720, 34, 19, "Syne", 600, "rgba(255,255,255,0.70)", "left", z=5),
        txt("footer-row2-b", "contact_row2", PAD + 18, 94, 720, 30, 15, "Syne", 400, "rgba(255,255,255,0.42)", "left", z=5),
        txt("footer-web-b", "business_website", PAD + 18, 132, 420, 30, 17, "Syne", 700, A, "left", z=5),
    ],
    [
        rect("footer-bg-c", 0, 0, 1080, HEIGHT, BLK, z=0),
        rect("footer-rule-c", PAD, 38, 968, 1, "rgba(255,255,255,0.12)", z=2),
        txt("footer-row1-c", "contact_row1", PAD, 66, 968, 34, 20, "Syne", 600, "rgba(255,255,255,0.72)", "center", z=5),
        txt("footer-row2-c", "contact_row2", PAD, 106, 968, 30, 15, "Syne", 400, "rgba(255,255,255,0.42)", "center", z=5),
        txt("footer-web-c", "business_website", PAD, 140, 968, 30, 17, "Syne", 700, A, "center", z=5),
    ],
]

def get(seed: int = 0, brand_seed: int | None = None, **kwargs) -> Dict:
    return package_blueprint(SEGMENT_TYPE, HEIGHT, VARIANTS, seed)
