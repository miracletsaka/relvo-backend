from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Optional, List, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.content_draft import ContentDraft
from app.dependencies.org import get_current_org

router = APIRouter(prefix="/content-drafts", tags=["content-drafts"])


class DraftPatch(BaseModel):
    hook:         Optional[str]            = None
    subheading:   Optional[str]            = None
    bullets:      Optional[List[str]]      = None
    proof:        Optional[str]            = None
    cta:          Optional[str]            = None
    body_text:    Optional[str]            = None
    hashtags:     Optional[str]            = None
    scheduled_at: Optional[datetime]       = None
    platform:     Optional[str]            = None
    status:       Optional[str]            = None
    structured:   Optional[Dict[str, Any]] = None


def _clean_text(x: Optional[str]) -> Optional[str]:
    if x is None:
        return None
    v = x.strip()
    return v if v else None


def _clean_bullets(xs: Optional[List[str]]) -> Optional[List[str]]:
    if xs is None:
        return None
    out = [str(x).strip() for x in xs if str(x).strip()]
    return out[:10] if out else None


@router.patch("/{draft_id}")
def patch_draft(
    draft_id: str,
    payload:  DraftPatch,
    org = Depends(get_current_org),          # ← NEW
    db:  Session = Depends(get_db),
):
    try:
        did = uuid.UUID(draft_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid draft id")

    d = db.execute(
        select(ContentDraft).where(
            ContentDraft.id     == did,
            ContentDraft.org_id == org.id,   # ← NEW — scoped to org
        )
    ).scalar_one_or_none()

    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")

    if payload.platform     is not None: d.platform  = _clean_text(payload.platform)
    if payload.status       is not None: d.status    = _clean_text(payload.status)
    if payload.body_text    is not None: d.body_text = _clean_text(payload.body_text)
    if payload.hashtags     is not None: d.hashtags  = _clean_text(payload.hashtags)
    if payload.scheduled_at is not None: d.scheduled_at = payload.scheduled_at

    current = d.structured or {}
    if isinstance(current, str):
        try:
            current = json.loads(current) or {}
        except Exception:
            current = {}

    if payload.structured is not None:
        if not isinstance(payload.structured, dict):
            raise HTTPException(status_code=400, detail="structured must be an object")
        current = {**current, **payload.structured}

    if payload.hook        is not None: current["hook"]       = _clean_text(payload.hook)
    if payload.subheading  is not None: current["subheading"] = _clean_text(payload.subheading)
    if payload.bullets     is not None: current["bullets"]    = _clean_bullets(payload.bullets)
    if payload.proof       is not None: current["proof"]      = _clean_text(payload.proof)
    if payload.cta         is not None: current["cta"]        = _clean_text(payload.cta)

    cleaned = {k: v for k, v in current.items() if v not in (None, "", [], {})}
    d.structured = cleaned if cleaned else None
    d.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(d)

    return {
        "ok":         True,
        "id":         str(d.id),
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }