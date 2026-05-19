from __future__ import annotations

import random
from typing import Any, Dict, List, Literal, Optional, TypedDict


RegionName = Literal[
    "full",
    "left",
    "right",
    "top",
    "bottom",
    "center",
    "bottom_right",
    "bottom_left",
    "top_right",
    "top_left",
]


CompositionStyle = Literal[
    "cinematic_lead_conversion",
    "premium_social_ad",
    "editorial_campaign",
    "luxury_offer",
    "split_conversion",
    "dark_saas_campaign",
]


class SafeZone(TypedDict):
    x: int
    y: int
    width: int
    height: int


class SegmentPlan(TypedDict, total=False):
    segment_type: str
    region: RegionName
    z_layer: int
    segment_height: int
    safe_zone: SafeZone
    visual_weight: float
    overlap_allowed: bool
    requires_isolation: bool
    role: str
    notes: str


class PageLayoutPlan(TypedDict):
    canvas_width: int
    canvas_height: int
    orientation: str
    composition_style: CompositionStyle
    segments: List[SegmentPlan]


def _choose(items: List[Any]) -> Any:
    return random.choice(items)


def _safe_zone(
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    canvas_width: int,
    canvas_height: int,
) -> SafeZone:
    x = max(0, min(x, canvas_width - 10))
    y = max(0, min(y, canvas_height - 10))
    width = max(10, min(width, canvas_width - x))
    height = max(10, min(height, canvas_height - y))

    return {
        "x": round(x),
        "y": round(y),
        "width": round(width),
        "height": round(height),
    }


def _style() -> CompositionStyle:
    return _choose(
        [
            "cinematic_lead_conversion",
            "premium_social_ad",
            "editorial_campaign",
            "luxury_offer",
            "split_conversion",
            "dark_saas_campaign",
        ]
    )


def plan_page_layout(
    *,
    page_goal: str = "lead_conversion_campaign",
    orientation: str = "landscape",
    canvas_width: int = 1920,
    canvas_height: Optional[int] = None,
) -> PageLayoutPlan:
    """
    Master layout planner.

    This does NOT generate shapes.
    This decides who owns each area before segment generation.

    Purpose:
    - stop hero_media, hero_text, and offer from fighting for the same canvas
    - create a single campaign composition
    - assign safe zones before generating sections
    """

    if orientation == "landscape":
        canvas_width = canvas_width or 1920
        canvas_height = canvas_height or 1080
    else:
        canvas_width = canvas_width or 1080
        canvas_height = canvas_height or 1350

    style = _style()

    if style in {"cinematic_lead_conversion", "dark_saas_campaign"}:
        segments: List[SegmentPlan] = [
            {
                "segment_type": "hero_media",
                "region": "full",
                "z_layer": 0,
                "segment_height": canvas_height,
                "safe_zone": _safe_zone(
                    x=0,
                    y=0,
                    width=canvas_width,
                    height=canvas_height,
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                ),
                "visual_weight": 0.95,
                "overlap_allowed": True,
                "requires_isolation": False,
                "role": "cinematic background media",
                "notes": "Full canvas visual layer. Must leave readable negative space for text.",
            },
            {
                "segment_type": "hero_text",
                "region": "left",
                "z_layer": 30,
                "segment_height": canvas_height,
                "safe_zone": _safe_zone(
                    x=int(canvas_width * 0.06),
                    y=int(canvas_height * 0.16),
                    width=int(canvas_width * 0.46),
                    height=int(canvas_height * 0.48),
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                ),
                "visual_weight": 1.0,
                "overlap_allowed": True,
                "requires_isolation": True,
                "role": "primary message",
                "notes": "Main headline area. Must not collide with offer block.",
            },
            {
                "segment_type": "offer",
                "region": "bottom_right",
                "z_layer": 40,
                "segment_height": int(canvas_height * 0.32),
                "safe_zone": _safe_zone(
                    x=int(canvas_width * 0.58),
                    y=int(canvas_height * 0.64),
                    width=int(canvas_width * 0.34),
                    height=int(canvas_height * 0.26),
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                ),
                "visual_weight": 0.62,
                "overlap_allowed": False,
                "requires_isolation": True,
                "role": "conversion offer panel",
                "notes": "Compact offer. Must stay isolated and not cross headline zone.",
            },
        ]

    elif style == "split_conversion":
        segments = [
            {
                "segment_type": "hero_media",
                "region": "right",
                "z_layer": 0,
                "segment_height": canvas_height,
                "safe_zone": _safe_zone(
                    x=int(canvas_width * 0.48),
                    y=0,
                    width=int(canvas_width * 0.52),
                    height=canvas_height,
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                ),
                "visual_weight": 0.85,
                "overlap_allowed": True,
                "requires_isolation": False,
                "role": "right-side media field",
                "notes": "Media dominates the right. Left side must remain clean for hero text.",
            },
            {
                "segment_type": "hero_text",
                "region": "left",
                "z_layer": 30,
                "segment_height": canvas_height,
                "safe_zone": _safe_zone(
                    x=int(canvas_width * 0.06),
                    y=int(canvas_height * 0.18),
                    width=int(canvas_width * 0.42),
                    height=int(canvas_height * 0.48),
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                ),
                "visual_weight": 1.0,
                "overlap_allowed": False,
                "requires_isolation": True,
                "role": "left primary message",
            },
            {
                "segment_type": "offer",
                "region": "bottom_left",
                "z_layer": 40,
                "segment_height": int(canvas_height * 0.28),
                "safe_zone": _safe_zone(
                    x=int(canvas_width * 0.06),
                    y=int(canvas_height * 0.72),
                    width=int(canvas_width * 0.42),
                    height=int(canvas_height * 0.22),
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                ),
                "visual_weight": 0.58,
                "overlap_allowed": False,
                "requires_isolation": True,
                "role": "supporting conversion offer",
            },
        ]

    elif style == "luxury_offer":
        segments = [
            {
                "segment_type": "hero_media",
                "region": "full",
                "z_layer": 0,
                "segment_height": canvas_height,
                "safe_zone": _safe_zone(
                    x=0,
                    y=0,
                    width=canvas_width,
                    height=canvas_height,
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                ),
                "visual_weight": 0.75,
                "overlap_allowed": True,
                "requires_isolation": False,
                "role": "dark premium atmosphere",
            },
            {
                "segment_type": "hero_text",
                "region": "top_left",
                "z_layer": 30,
                "segment_height": canvas_height,
                "safe_zone": _safe_zone(
                    x=int(canvas_width * 0.08),
                    y=int(canvas_height * 0.12),
                    width=int(canvas_width * 0.48),
                    height=int(canvas_height * 0.36),
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                ),
                "visual_weight": 0.9,
                "overlap_allowed": False,
                "requires_isolation": True,
                "role": "luxury campaign headline",
            },
            {
                "segment_type": "offer",
                "region": "center",
                "z_layer": 40,
                "segment_height": int(canvas_height * 0.36),
                "safe_zone": _safe_zone(
                    x=int(canvas_width * 0.28),
                    y=int(canvas_height * 0.56),
                    width=int(canvas_width * 0.44),
                    height=int(canvas_height * 0.3),
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                ),
                "visual_weight": 0.78,
                "overlap_allowed": False,
                "requires_isolation": True,
                "role": "premium centered offer",
            },
        ]

    else:
        segments = [
            {
                "segment_type": "hero_media",
                "region": "full",
                "z_layer": 0,
                "segment_height": canvas_height,
                "safe_zone": _safe_zone(
                    x=0,
                    y=0,
                    width=canvas_width,
                    height=canvas_height,
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                ),
                "visual_weight": 0.88,
                "overlap_allowed": True,
                "requires_isolation": False,
                "role": "full background campaign media",
            },
            {
                "segment_type": "hero_text",
                "region": "center",
                "z_layer": 30,
                "segment_height": canvas_height,
                "safe_zone": _safe_zone(
                    x=int(canvas_width * 0.18),
                    y=int(canvas_height * 0.18),
                    width=int(canvas_width * 0.64),
                    height=int(canvas_height * 0.36),
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                ),
                "visual_weight": 1.0,
                "overlap_allowed": False,
                "requires_isolation": True,
                "role": "center editorial message",
            },
            {
                "segment_type": "offer",
                "region": "bottom",
                "z_layer": 40,
                "segment_height": int(canvas_height * 0.26),
                "safe_zone": _safe_zone(
                    x=int(canvas_width * 0.18),
                    y=int(canvas_height * 0.68),
                    width=int(canvas_width * 0.64),
                    height=int(canvas_height * 0.22),
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                ),
                "visual_weight": 0.6,
                "overlap_allowed": False,
                "requires_isolation": True,
                "role": "bottom conversion strip",
            },
        ]

    return {
        "canvas_width": canvas_width,
        "canvas_height": canvas_height,
        "orientation": orientation,
        "composition_style": style,
        "segments": segments,
    }