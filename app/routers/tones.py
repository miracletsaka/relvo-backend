"""
app/routers/tones.py
─────────────────────
Tone management endpoints.

New logic:
- Human gives a simple tone idea.
- AI can generate name/label/description/emoji/suggested segments.
- Tone stores core fields in tones table.
- Extra allowed segments are stored in tone_segments.
- Default segments are not stored because they are always included globally.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.tone import Tone

router = APIRouter(prefix="/tones", tags=["tones"])
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_SEGMENTS = ["background", "hero-image", "hero-text", "cta", "footer"]
EXTRA_SEGMENTS = ["features", "offer", "sponsors", "contact", "social", "reviews", "scene", "header"]


class ToneCreate(BaseModel):
    name: str
    label: str
    description: Optional[str] = None
    emoji: Optional[str] = None
    sort_order: Optional[int] = 0
    is_active: Optional[bool] = True
    segment_types: list[str] = []


class TonePatch(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    emoji: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    segment_types: Optional[list[str]] = None


class ToneGenerateRequest(BaseModel):
    idea: str


def _slugify_tone_name(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:80] or "custom_tone"


def _clean_segment_types(segment_types: list[str] | None) -> list[str]:
    if not segment_types:
        return []

    allowed = set(EXTRA_SEGMENTS)
    cleaned: list[str] = []

    for segment in segment_types:
        segment = str(segment or "").strip()
        if segment in allowed and segment not in cleaned:
            cleaned.append(segment)

    return cleaned


def _get_or_404(db: Session, tone_id: str) -> Tone:
    try:
        uid = uuid.UUID(tone_id)
    except ValueError:
        raise HTTPException(400, "Invalid tone ID")

    tone = db.execute(select(Tone).where(Tone.id == uid)).scalars().first()
    if not tone:
        raise HTTPException(404, "Tone not found")

    return tone


def _get_tone_segments(db: Session, tone_id) -> list[str]:
    rows = db.execute(
        text("""
            SELECT segment_type
            FROM tone_segments
            WHERE tone_id = :tone_id
            ORDER BY segment_type ASC
        """),
        {"tone_id": str(tone_id)},
    ).fetchall()

    return [row[0] for row in rows]


def _replace_tone_segments(db: Session, tone_id, segment_types: list[str] | None) -> None:
    cleaned = _clean_segment_types(segment_types)

    db.execute(
        text("DELETE FROM tone_segments WHERE tone_id = :tone_id"),
        {"tone_id": str(tone_id)},
    )

    for segment_type in cleaned:
        db.execute(
            text("""
                INSERT INTO tone_segments (tone_id, segment_type)
                VALUES (:tone_id, :segment_type)
                ON CONFLICT (tone_id, segment_type) DO NOTHING
            """),
            {"tone_id": str(tone_id), "segment_type": segment_type},
        )


def _tone_to_dict(db: Session, tone: Tone) -> dict:
    data = tone.to_dict()
    extra_segments = _get_tone_segments(db, tone.id)
    data["segment_types"] = extra_segments
    data["default_segments"] = DEFAULT_SEGMENTS
    data["all_segments"] = DEFAULT_SEGMENTS + extra_segments
    return data


def _safe_ai_json(raw: str) -> dict:
    raw = (raw or "").strip()
    try:
        return json.loads(raw)
    except Exception:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except Exception:
            pass

    return {}


def _fallback_generated_tone(idea: str) -> dict:
    words = [w for w in re.sub(r"[^a-zA-Z0-9 ]+", " ", idea).split() if len(w) > 2]
    label = " ".join(words[:3]).strip().title() or "Custom Tone"
    return {
        "name": _slugify_tone_name(label),
        "label": label,
        "description": "Use a clear, practical, business-focused tone. Keep the message human, confident, concise, and action-oriented.",
        "emoji": "✨",
        "suggested_segments": ["features", "cta"] if "cta" in EXTRA_SEGMENTS else ["features"],
    }


@router.get("")
def list_tones(active_only: bool = True, db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = select(Tone).order_by(Tone.sort_order.asc(), Tone.name.asc())
    if active_only:
        q = q.where(Tone.is_active == True)  # noqa: E712
    rows = db.execute(q).scalars().all()
    return [_tone_to_dict(db, row) for row in rows]


@router.post("/generate")
def generate_tone(payload: ToneGenerateRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    idea = (payload.idea or "").strip()
    if not idea:
        raise HTTPException(status_code=400, detail="Tone idea is required")

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.55,
            messages=[
                {
                    "role": "system",
                    "content": f"""
You generate tone presets for an AI marketing/design system.

Return STRICT JSON only. No markdown. No explanations.

Available extra segments:
{', '.join(EXTRA_SEGMENTS)}

Default segments are always included automatically and must NOT be returned:
{', '.join(DEFAULT_SEGMENTS)}

JSON shape:
{{
  "name": "lowercase_slug_with_underscores",
  "label": "Human Label",
  "description": "Instruction for how AI should write/design using this tone. 1-2 concise sentences.",
  "emoji": "single emoji",
  "suggested_segments": ["features", "offer"]
}}

Rules:
- name must be lowercase letters/numbers/underscores only.
- suggested_segments must only contain items from available extra segments.
- Choose segments that support the tone. Do not select everything.
- If unsure, suggest ["features"].
""",
                },
                {"role": "user", "content": idea},
            ],
        )
        data = _safe_ai_json(res.choices[0].message.content or "") or _fallback_generated_tone(idea)
    except Exception:
        data = _fallback_generated_tone(idea)

    name = _slugify_tone_name(str(data.get("name") or data.get("label") or idea))
    label = str(data.get("label") or name.replace("_", " ").title()).strip()
    description = str(data.get("description") or _fallback_generated_tone(idea)["description"]).strip()
    emoji = str(data.get("emoji") or "✨").strip()[:10]
    suggested_segments = _clean_segment_types(data.get("suggested_segments") or []) or ["features"]

    existing = db.execute(select(Tone).where(Tone.name == name)).scalars().first()
    if existing:
        suffix = 2
        base_name = name
        while db.execute(select(Tone).where(Tone.name == f"{base_name}_{suffix}")).scalars().first():
            suffix += 1
        name = f"{base_name}_{suffix}"

    return {
        "name": name,
        "label": label,
        "description": description,
        "emoji": emoji,
        "suggested_segments": suggested_segments,
        "default_segments": DEFAULT_SEGMENTS,
        "available_extra_segments": EXTRA_SEGMENTS,
    }


@router.post("", status_code=201)
def create_tone(payload: ToneCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    name = _slugify_tone_name(payload.name)
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
    db.flush()
    _replace_tone_segments(db, tone.id, payload.segment_types)
    db.commit()
    db.refresh(tone)
    return _tone_to_dict(db, tone)


@router.patch("/{tone_id}")
def update_tone(tone_id: str, payload: TonePatch, db: Session = Depends(get_db), user=Depends(get_current_user)):
    tone = _get_or_404(db, tone_id)
    data = payload.model_dump(exclude_unset=True)
    segment_types = data.pop("segment_types", None)

    for field, value in data.items():
        setattr(tone, field, value)

    if segment_types is not None:
        _replace_tone_segments(db, tone.id, segment_types)

    db.commit()
    db.refresh(tone)
    return _tone_to_dict(db, tone)


@router.delete("/{tone_id}", status_code=204)
def delete_tone(tone_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    tone = _get_or_404(db, tone_id)
    db.delete(tone)
    db.commit()
