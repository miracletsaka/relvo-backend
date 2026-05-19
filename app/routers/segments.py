from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.ai_composition_generator import generate_ai_composition
from app.services.ai_segment_generator import generate_ai_segment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/segments", tags=["segments"])


class GenerateSegmentPayload(BaseModel):
    segment_type: str
    brand_id: Optional[str] = None
    tone_id: Optional[str] = None
    canvas_width: int = 1920
    segment_height: Optional[int] = None
    orientation: str = "landscape"
    save: bool = False

    brand_name: Optional[str] = None
    brand_color: Optional[str] = None
    tone_name: Optional[str] = None


@router.post("/generate")
def generate_segment(payload: GenerateSegmentPayload):
    logger.info("Generating segment with payload: %s", payload)

    brand_name = payload.brand_name or "NeuroFlow AI"
    brand_color = payload.brand_color or "__BRAND_ACCENT__"
    tone_name = payload.tone_name or "Premium"

    if payload.segment_type in {
        "campaign_composition",
        "composition",
        "full_composition",
        "master_composition",
    }:
        generated = generate_ai_composition(
            brand_name=brand_name,
            brand_color=brand_color,
            tone_name=tone_name,
            page_goal="lead_conversion_campaign",
            canvas_width=payload.canvas_width or 1920,
            canvas_height=payload.segment_height or 1080,
            orientation=payload.orientation or "landscape",
        )

        return {
            "ok": True,
            "saved": False,
            "segment": generated,
        }

    generated = generate_ai_segment(
        segment_type=payload.segment_type,
        brand_name=brand_name,
        brand_color=brand_color,
        tone_name=tone_name,
        canvas_width=payload.canvas_width,
        segment_height=payload.segment_height,
        orientation=payload.orientation,
    )

    return {
        "ok": True,
        "saved": False,
        "segment": generated,
    }