from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.services.ai_layout_planner import plan_page_layout
from app.services.ai_segment_generator import generate_ai_segment

logger = logging.getLogger(__name__)


def _int(value: Any, fallback: int) -> int:
    try:
        return int(float(value))
    except Exception:
        return fallback


def _offset_shape(
    shape: Dict[str, Any],
    *,
    offset_x: int,
    offset_y: int,
    z_offset: int,
) -> Dict[str, Any]:
    return {
        **shape,
        "x": _int(shape.get("x"), 0) + offset_x,
        "y": _int(shape.get("y"), 0) + offset_y,
        "zIndex": _int(shape.get("zIndex"), 0) + z_offset,
    }


def _offset_segment_shapes(
    *,
    segment: Dict[str, Any],
    offset_x: int,
    offset_y: int,
    z_layer: int,
) -> List[Dict[str, Any]]:
    shapes = segment.get("shapes") or []

    if not isinstance(shapes, list):
        return []

    return [
        _offset_shape(
            shape,
            offset_x=offset_x,
            offset_y=offset_y,
            z_offset=z_layer,
        )
        for shape in shapes
        if isinstance(shape, dict)
    ]


def generate_ai_composition(
    *,
    brand_name: str,
    brand_color: str,
    tone_name: str,
    page_goal: str = "lead_conversion_campaign",
    canvas_width: int = 1920,
    canvas_height: int = 1080,
    orientation: str = "landscape",
) -> Dict[str, Any]:
    """
    Master composition generator.

    This is the orchestration layer:
    1. Plan full-page layout.
    2. Generate each segment inside its assigned zone.
    3. Offset shapes into final canvas.
    4. Return one coordinated composition.
    """

    plan = plan_page_layout(
        page_goal=page_goal,
        orientation=orientation,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
    )

    final_shapes: List[Dict[str, Any]] = []
    generated_segments: List[Dict[str, Any]] = []

    for item in plan["segments"]:
        segment_type = item["segment_type"]
        safe_zone = item["safe_zone"]
        region = item.get("region", "full")
        z_layer = _int(item.get("z_layer"), 0)

        safe_x = _int(safe_zone.get("x"), 0)
        safe_y = _int(safe_zone.get("y"), 0)
        safe_w = _int(safe_zone.get("width"), canvas_width)
        safe_h = _int(safe_zone.get("height"), canvas_height)

        logger.info(
            "composition segment: type=%s region=%s safe_zone=%s z=%s",
            segment_type,
            region,
            safe_zone,
            z_layer,
        )

        if region == "full":
            generated = generate_ai_segment(
                segment_type=segment_type,
                brand_name=brand_name,
                brand_color=brand_color,
                tone_name=tone_name,
                canvas_width=canvas_width,
                segment_height=canvas_height,
                orientation=orientation,
            )

            segment_shapes = _offset_segment_shapes(
                segment=generated,
                offset_x=0,
                offset_y=0,
                z_layer=z_layer,
            )

        else:
            generated = generate_ai_segment(
                segment_type=segment_type,
                brand_name=brand_name,
                brand_color=brand_color,
                tone_name=tone_name,
                canvas_width=safe_w,
                segment_height=safe_h,
                orientation=orientation,
            )

            segment_shapes = _offset_segment_shapes(
                segment=generated,
                offset_x=safe_x,
                offset_y=safe_y,
                z_layer=z_layer,
            )

        final_shapes.extend(segment_shapes)

        generated_segments.append(
            {
                "segment_type": segment_type,
                "region": region,
                "z_layer": z_layer,
                "safe_zone": safe_zone,
                "generated_name": generated.get("name"),
                "generated_description": generated.get("description"),
                "shape_count": len(segment_shapes),
            }
        )

    final_shapes = sorted(final_shapes, key=lambda s: _int(s.get("zIndex"), 0))

    return {
        "name": "AI Coordinated Campaign Composition",
        "description": f"Master-planned {plan['composition_style']} composition",
        "composition_style": plan["composition_style"],
        "canvas_width": plan["canvas_width"],
        "canvas_height": plan["canvas_height"],
        "orientation": plan["orientation"],
        "segment_height": plan["canvas_height"],
        "segments": generated_segments,
        "shapes": final_shapes,
    }