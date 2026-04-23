import uuid
import json
import random
from datetime import datetime
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, select, desc

from app.database import get_db
from app.dependencies.org import get_current_org
from app.models.template import Template
from app.models.templateServe import TemplateServe
from app.models.tone import Tone
from app.services.template_synthesizer import synthesize_template_from_examples

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateCreateRequest(BaseModel):
    brand_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    shapes: Any
    canvasWidth: int
    canvasHeight: int
    backgroundImage: Optional[str] = None
    logoPlacement: Optional[Any] = None
    thumbnail_url: Optional[str] = None
    preview_url: Optional[str] = None
    tone_id: Optional[str] = None
    orientation: Optional[str] = None


class SynthesizeTemplateReq(BaseModel):
    brand_id: Optional[str] = "neuroflow"
    canvas_width: Optional[int] = 1080
    canvas_height: Optional[int] = 1350


class TemplateUpdateRequest(BaseModel):
    brand_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    shapes: Optional[Any] = None
    canvasWidth: Optional[int] = None
    canvasHeight: Optional[int] = None
    backgroundImage: Optional[str] = None
    logoPlacement: Optional[Any] = None
    thumbnail_url: Optional[str] = None
    preview_url: Optional[str] = None
    tone_id: Optional[str] = None
    orientation: Optional[str] = None


def _serialize_template(t: Template, tone: Optional[Tone] = None):
    return {
        "id": t.id,
        "brand_id": t.brand_id,
        "tone_id": t.tone_id,
        "tone_name": tone.name if tone else None,
        "tone_label": tone.label if tone else None,
        "name": t.name,
        "description": t.description,
        "shapes": json.loads(t.shapes_json or "[]"),
        "canvasWidth": int(t.canvas_width) if t.canvas_width is not None else None,
        "canvasHeight": int(t.canvas_height) if t.canvas_height is not None else None,
        "orientation": t.orientation,
        "backgroundImage": t.background_image,
        "logoPlacement": json.loads(t.logo_placement_json) if t.logo_placement_json else None,
        "thumbnail_url": t.thumbnail_url,
        "preview_url": t.preview_url,
        "createdAt": t.created_at.isoformat() if t.created_at else None,
        "updatedAt": t.updated_at.isoformat() if t.updated_at else None,
    }


def _get_template_for_org(template_id: str, org, db: Session):
    tpl = db.query(Template).filter(
        Template.id == template_id,
        Template.org_id == str(org.id),
    ).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl


def _get_tone_for_org_or_global(db: Session, tone_id: str):
    tone = db.query(Tone).filter(Tone.id == tone_id).first()
    if not tone:
        raise HTTPException(status_code=400, detail="Selected tone not found")
    return tone


@router.get("/random")
def get_random_template(
    brand_id: Optional[str] = Query(None),
    tone_id: Optional[str] = Query(None),
    orientation: Optional[str] = Query(None),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
):
    base_q = select(Template).where(Template.org_id == str(org.id))

    if brand_id:
        base_q = base_q.where(Template.brand_id == brand_id)

    if tone_id:
        base_q = base_q.where(Template.tone_id == tone_id)

    if orientation:
        base_q = base_q.where(Template.orientation == orientation)

    served_subq = select(TemplateServe.template_id).where(
        TemplateServe.org_id == org.id
    )

    template = db.execute(
        base_q.where(~Template.id.in_(served_subq)).order_by(func.random())
    ).scalars().first()

    if not template:
        template = db.execute(
            base_q.order_by(func.random())
        ).scalars().first()

    if not template:
        return {"success": False, "reason": "no_templates_found"}

    try:
        db.add(TemplateServe(
            template_id=template.id,
            org_id=org.id,
            brand_id=brand_id,
            tone_id=tone_id,
            orientation=orientation,
        ))
        db.commit()
    except Exception:
        db.rollback()

    tone = None
    if template.tone_id:
        tone = db.query(Tone).filter(Tone.id == template.tone_id).first()

    return _serialize_template(template, tone)


@router.patch("/{template_id}")
def update_template(
    template_id: str,
    payload: TemplateUpdateRequest,
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
):
    tpl = _get_template_for_org(template_id, org, db)

    if payload.brand_id is not None:
        tpl.brand_id = payload.brand_id

    if payload.name is not None:
        tpl.name = payload.name.strip()

    if payload.description is not None:
        tpl.description = payload.description

    if payload.shapes is not None:
        try:
            tpl.shapes_json = json.dumps(payload.shapes, ensure_ascii=False)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid shapes JSON: {e}")

    if payload.canvasWidth is not None:
        tpl.canvas_width = str(int(payload.canvasWidth))

    if payload.canvasHeight is not None:
        tpl.canvas_height = str(int(payload.canvasHeight))

    if payload.backgroundImage is not None:
        tpl.background_image = payload.backgroundImage

    if payload.logoPlacement is not None:
        try:
            tpl.logo_placement_json = json.dumps(payload.logoPlacement, ensure_ascii=False)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid logoPlacement JSON: {e}")

    if payload.thumbnail_url is not None:
        tpl.thumbnail_url = payload.thumbnail_url

    if payload.preview_url is not None:
        tpl.preview_url = payload.preview_url

    if payload.tone_id is not None:
        if payload.tone_id:
            _get_tone_for_org_or_global(db, payload.tone_id)
            tpl.tone_id = payload.tone_id
        else:
            tpl.tone_id = None

    if payload.orientation is not None:
        if payload.orientation not in ("portrait", "landscape"):
            raise HTTPException(status_code=400, detail="Invalid orientation")
        tpl.orientation = payload.orientation

    tpl.updated_at = datetime.utcnow()
    db.add(tpl)
    db.commit()
    db.refresh(tpl)

    tone = None
    if tpl.tone_id:
        tone = db.query(Tone).filter(Tone.id == tpl.tone_id).first()

    return {
        "ok": True,
        "id": tpl.id,
        "template": _serialize_template(tpl, tone),
    }


@router.post("")
def create_template(
    payload: TemplateCreateRequest,
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
):
    if payload.tone_id:
        _get_tone_for_org_or_global(db, payload.tone_id)

    if payload.orientation and payload.orientation not in ("portrait", "landscape"):
        raise HTTPException(status_code=400, detail="Invalid orientation")

    tid = str(uuid.uuid4())
    now = datetime.utcnow()

    row = Template(
        id=tid,
        brand_id=payload.brand_id,
        org_id=str(org.id),
        name=payload.name,
        description=payload.description,
        shapes_json=json.dumps(payload.shapes, ensure_ascii=False),
        canvas_width=str(payload.canvasWidth),
        canvas_height=str(payload.canvasHeight),
        background_image=payload.backgroundImage,
        logo_placement_json=json.dumps(payload.logoPlacement, ensure_ascii=False) if payload.logoPlacement else None,
        thumbnail_url=payload.thumbnail_url,
        preview_url=payload.preview_url,
        tone_id=payload.tone_id,
        orientation=payload.orientation or "portrait",
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    return {"ok": True, "id": tid}


@router.get("")
def list_templates(
    brand_id: Optional[str] = Query(None),
    tone_id: Optional[str] = Query(None),
    orientation: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
):
    q = (
        select(Template, Tone)
        .select_from(Template)
        .outerjoin(Tone, Tone.id == Template.tone_id)
        .where(Template.org_id == str(org.id))
        .order_by(desc(Template.updated_at), desc(Template.created_at))
        .limit(limit)
    )

    if brand_id:
        q = q.where(Template.brand_id == brand_id)

    if tone_id:
        q = q.where(Template.tone_id == tone_id)

    if orientation:
        q = q.where(Template.orientation == orientation)

    rows = db.execute(q).all()

    return [
        _serialize_template(template_row, tone_row)
        for template_row, tone_row in rows
    ]


@router.get("/{template_id}")
def get_template(
    template_id: str,
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
):
    tpl = _get_template_for_org(template_id, org, db)

    tone = None
    if tpl.tone_id:
        tone = db.query(Tone).filter(Tone.id == tpl.tone_id).first()

    return _serialize_template(tpl, tone)


@router.delete("/{template_id}")
def delete_template(
    template_id: str,
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
):
    tpl = _get_template_for_org(template_id, org, db)
    db.delete(tpl)
    db.commit()
    return {"ok": True, "deleted": True, "id": template_id}


@router.post("/synthesize-and-save")
def synthesize_and_save_template(
    payload: SynthesizeTemplateReq,
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
):
    brand_id = payload.brand_id or "neuroflow"
    canvas_width = payload.canvas_width or 1080
    canvas_height = payload.canvas_height or 1350

    templates = db.query(Template).filter(
        Template.shapes_json.isnot(None),
        Template.org_id == str(org.id),
    ).limit(50).all()

    if len(templates) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 templates in DB")

    picked = random.sample(templates, k=min(2, len(templates)))
    example_templates = []
    used_ids = []

    for t in picked:
        used_ids.append(t.id)
        try:
            shapes = json.loads(t.shapes_json or "[]")
        except Exception:
            shapes = []

        logo = None
        if t.logo_placement_json:
            try:
                logo = json.loads(t.logo_placement_json)
            except Exception:
                logo = None

        example_templates.append({
            "id": t.id,
            "canvasWidth": int(t.canvas_width) if t.canvas_width else canvas_width,
            "canvasHeight": int(t.canvas_height) if t.canvas_height else canvas_height,
            "shapes": shapes,
            "backgroundImage": t.background_image,
            "logoPlacement": logo,
            "orientation": t.orientation,
        })

    synthesized = synthesize_template_from_examples(
        example_templates=example_templates,
        brand_id=brand_id,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
    )

    shapes_out = synthesized.get("shapes") if isinstance(synthesized, dict) else None
    if not isinstance(shapes_out, list) or len(shapes_out) == 0:
        raise HTTPException(status_code=400, detail="Synthesis failed: no shapes returned")

    new_id = str(uuid.uuid4())
    name = (synthesized.get("name") if isinstance(synthesized, dict) else None) or "AI Premium Template"

    new_tpl = Template(
        id=new_id,
        brand_id=brand_id,
        org_id=str(org.id),
        name=name,
        description=f"Generated from templates: {', '.join(used_ids)}",
        shapes_json=json.dumps(shapes_out, ensure_ascii=False),
        canvas_width=str(int(synthesized.get("canvasWidth") or canvas_width)),
        canvas_height=str(int(synthesized.get("canvasHeight") or canvas_height)),
        background_image=synthesized.get("backgroundImage"),
        logo_placement_json=json.dumps(synthesized.get("logoPlacement"), ensure_ascii=False) if synthesized.get("logoPlacement") else None,
        orientation=synthesized.get("orientation"),
        thumbnail_url=synthesized.get("thumbnail_url"),
        preview_url=synthesized.get("preview_url"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(new_tpl)
    db.commit()
    db.refresh(new_tpl)

    return {
        "ok": True,
        "template": _serialize_template(new_tpl),
        "used_templates": used_ids,
    }