"""
app/routers/tones.py
─────────────────────
Tone management endpoints.

Mount in main.py:
    from app.routers import tones
    app.include_router(tones.router)
"""
from __future__ import annotations

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.tone import Tone

router = APIRouter(prefix="/tones", tags=["tones"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ToneCreate(BaseModel):
    name: str
    label: str
    description: Optional[str] = None
    emoji: Optional[str] = None
    sort_order: Optional[int] = 0
    is_active: Optional[bool] = True


class TonePatch(BaseModel):
    label:       Optional[str]  = None
    description: Optional[str]  = None
    emoji:       Optional[str]  = None
    sort_order:  Optional[int]  = None
    is_active:   Optional[bool] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("")
def list_tones(
    active_only: bool = True,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    q = select(Tone).order_by(Tone.sort_order.asc(), Tone.name.asc())
    if active_only:
        q = q.where(Tone.is_active == True)  # noqa: E712
    rows = db.execute(q).scalars().all()
    return [r.to_dict() for r in rows]


@router.post("", status_code=201)
def create_tone(
    payload: ToneCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    name = payload.name.strip().lower().replace(" ", "_").replace("-", "_")

    existing = db.execute(select(Tone).where(Tone.name == name)).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Tone '{name}' already exists")

    tone = Tone(
        id=uuid.uuid4(),
        name=name,
        label=payload.label.strip(),
        description=payload.description,
        emoji=payload.emoji,
        sort_order=payload.sort_order or 0,
        is_active=True if payload.is_active is None else payload.is_active,
    )

    db.add(tone)
    db.commit()
    db.refresh(tone)
    return tone.to_dict()


@router.patch("/{tone_id}")
def update_tone(
    tone_id: str,
    payload: TonePatch,
    db:      Session = Depends(get_db),
    user             = Depends(get_current_user),
):
    tone = _get_or_404(db, tone_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tone, field, value)
    db.commit()
    db.refresh(tone)
    return tone.to_dict()


@router.delete("/{tone_id}", status_code=204)
def delete_tone(
    tone_id: str,
    db:      Session = Depends(get_db),
    user             = Depends(get_current_user),
):
    tone = _get_or_404(db, tone_id)
    db.delete(tone)
    db.commit()


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_or_404(db: Session, tone_id: str) -> Tone:
    try:
        uid = uuid.UUID(tone_id)
    except ValueError:
        raise HTTPException(400, "Invalid tone ID")
    tone = db.execute(select(Tone).where(Tone.id == uid)).scalars().first()
    if not tone:
        raise HTTPException(404, "Tone not found")
    return tone