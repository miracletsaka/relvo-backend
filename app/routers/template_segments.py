import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db

from app.models.template_segment import TemplateSegment

from app.schemas.template_segments import (
    TemplateSegmentCreate,
    TemplateSegmentUpdate,
    TemplateSegmentOut,
)

from app.dependencies.org import get_current_org


router = APIRouter(
    prefix="/template-segments",
    tags=["template-segments"],
)


@router.post("", response_model=TemplateSegmentOut, status_code=201)
def create_template_segment(
    payload: TemplateSegmentCreate,
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    segment = TemplateSegment(
        id=uuid.uuid4(),

        org_id=org.id,

        template_family=payload.template_family,
        segment_key=payload.segment_key,

        name=payload.name,
        description=payload.description,

        shapes_json=payload.shapes_json,

        canvas_width=payload.canvas_width,
        canvas_height=payload.canvas_height,

        compatible_tones=payload.compatible_tones,
        compatible_categories=payload.compatible_categories,

        preview_url=payload.preview_url,
        thumbnail_url=payload.thumbnail_url,

        generation_source=payload.generation_source,

        tags=payload.tags,

        is_system=payload.is_system,

        created_at=now,
        updated_at=now,
    )

    db.add(segment)
    db.commit()
    db.refresh(segment)

    return segment


@router.get("", response_model=list[TemplateSegmentOut])
def list_template_segments(
    template_family: str | None = None,
    segment_key: str | None = None,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
):
    q = db.query(TemplateSegment).filter(
        TemplateSegment.org_id == org.id
    )

    if template_family:
        q = q.filter(
            TemplateSegment.template_family == template_family
        )

    if segment_key:
        q = q.filter(
            TemplateSegment.segment_key == segment_key
        )

    return (
        q.order_by(
            TemplateSegment.created_at.desc()
        )
        .all()
    )

@router.get("/compose-random")
def compose_random_template(
    template_family: str = "mixed-poster",
    sections: str | None = None,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
):
    default_sections = [
        "background",
        "scene",
        "hero-image",
        "header",
        "hero-text",
        "offer",
        "cta",
        "footer",
    ]

    required_sections = {
        "background",
        "hero-image",
        "hero-text",
        "cta",
        "footer",
    }

    segment_order = (
        [s.strip() for s in sections.split(",") if s.strip()]
        if sections
        else default_sections
    )

    picked = []
    missing_required = []
    skipped_optional = []

    for segment_key in segment_order:
        row = (
            db.query(TemplateSegment)
            .filter(
                TemplateSegment.org_id == org.id,
                TemplateSegment.template_family == template_family,
                TemplateSegment.segment_key == segment_key,
            )
            .order_by(func.random())
            .first()
        )

        if not row:
            if segment_key in required_sections:
                missing_required.append(segment_key)
            else:
                skipped_optional.append(segment_key)
            continue

        picked.append(row)

    if missing_required:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Missing required segment types",
                "missing_required": missing_required,
                "skipped_optional": skipped_optional,
            },
        )

    shapes = []

    for segment in picked:
        shapes.extend(segment.shapes_json or [])

    return {
        "instanceId": f"db-composed-{template_family}",
        "requested_type": "campaign_composition",
        "name": "DB Mixed Poster",
        "description": "Randomly composed from selected saved template segments.",
        "segment_type": "campaign_composition",
        "internal_segment_type": "campaign_composition",
        "segment_height": 1350,
        "y": 0,
        "shapes": shapes,
        "picked_segments": [
            {
                "id": str(segment.id),
                "segment_key": segment.segment_key,
                "name": segment.name,
            }
            for segment in picked
        ],
        "skipped_optional": skipped_optional,
    }


@router.get("/{segment_id}", response_model=TemplateSegmentOut)
def get_template_segment(
    segment_id: str,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
):
    segment = (
        db.query(TemplateSegment)
        .filter(
            TemplateSegment.id == segment_id,
            TemplateSegment.org_id == org.id,
        )
        .first()
    )

    if not segment:
        raise HTTPException(
            status_code=404,
            detail="Template segment not found",
        )

    return segment


@router.patch("/{segment_id}", response_model=TemplateSegmentOut)
def update_template_segment(
    segment_id: str,
    payload: TemplateSegmentUpdate,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
):
    segment = (
        db.query(TemplateSegment)
        .filter(
            TemplateSegment.id == segment_id,
            TemplateSegment.org_id == org.id,
        )
        .first()
    )

    if not segment:
        raise HTTPException(
            status_code=404,
            detail="Template segment not found",
        )

    updates = payload.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(segment, key, value)

    segment.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(segment)

    return segment


@router.delete("/{segment_id}", status_code=204)
def delete_template_segment(
    segment_id: str,
    db: Session = Depends(get_db),
    org=Depends(get_current_org),
):
    segment = (
        db.query(TemplateSegment)
        .filter(
            TemplateSegment.id == segment_id,
            TemplateSegment.org_id == org.id,
        )
        .first()
    )

    if not segment:
        raise HTTPException(
            status_code=404,
            detail="Template segment not found",
        )

    db.delete(segment)
    db.commit()