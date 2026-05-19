# backend/app/routers/generation.py
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.content_item import ContentItem
from app.models.content_draft import ContentDraft
from app.services.ai_generator import generate_post
from app.models.tone import Tone
import random

router = APIRouter(prefix="/generation", tags=["generation"])

def _pick_random_tone(
    db: Session,
    requested_tone_id: str | None = None,
):
    # Explicit tone requested
    if requested_tone_id:
        try:
            tone_uuid = uuid.UUID(str(requested_tone_id))

            tone = (
                db.execute(
                    select(Tone).where(
                        Tone.id == tone_uuid,
                        Tone.is_active == True,  # noqa
                    )
                )
                .scalars()
                .first()
            )

            if tone:
                return tone

        except Exception:
            pass

    # Random active tone
    tones = (
        db.execute(
            select(Tone).where(
                Tone.is_active == True  # noqa
            )
        )
        .scalars()
        .all()
    )

    if not tones:
        return None

    return random.choice(tones)

class GenerateDraftsRequest(BaseModel):
    brand_id: str

    # Old modes still supported:
    # "new" | "rejected" | "monthly"
    #
    # New temporary demo mode:
    # "single" — generate exactly one draft directly from payload.topic.
    mode: str = Field(default="new")

    # New direct prompt/topic input for AI chat demo.
    topic: str | None = None

    # Optional tone fields. If the caller already has tone metadata,
    # pass it here. Otherwise generation still works without it.
    tone_id: str | None = None
    tone_name: str | None = None
    tone_label: str | None = None
    tone_description: str | None = None
    tone_prompt_instruction: str | None = None

    platforms: list[str] | None = None

    # Monthly fields are ignored for mode="single".
    target_month: str | None = None
    posts_per_week: int | None = None

    brand_profile_summary: str | None = None
    brand_profile_json: object | None = None

    client_now: Optional[str] = None
    timezone: Optional[str] = None
    posting_hour_local: Optional[int] = 9

    # Optional DB/org enrichment already built by another service.
    # If passed, generate_post will merge it into structured output.
    org_context_block: str | None = None
    org_structured_patch: dict | None = None


def _parse_iso_utc(dt_str: str) -> Optional[datetime]:
    if not dt_str:
        return None

    try:
        iso = str(dt_str).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _parse_client_now(client_now: Optional[str]) -> datetime:
    if not client_now:
        return datetime.now(timezone.utc)

    try:
        dt = datetime.fromisoformat(client_now.replace("Z", "+00:00"))

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _bump_if_past(scheduled_utc: Optional[datetime], min_utc: datetime) -> Optional[datetime]:
    if not scheduled_utc:
        return None

    if scheduled_utc < min_utc:
        return (min_utc + timedelta(minutes=60)).replace(second=0, microsecond=0)

    return scheduled_utc


def _normalize_hashtags(result: dict, structured: dict) -> str:
    h = result.get("hashtags") or structured.get("hashtags") or ""

    if isinstance(h, list):
        return " ".join([str(x).strip() for x in h if str(x).strip()]).strip()

    return str(h).strip()


def _scheduled_dt_from_result(
    result: dict,
    structured: dict,
    client_now: Optional[str],
) -> Optional[datetime]:
    client_now_utc = _parse_client_now(client_now)
    ai_scheduled = result.get("scheduled_at") or structured.get("scheduled_at")
    dt_utc = _parse_iso_utc(ai_scheduled) if ai_scheduled else None
    dt_utc = _bump_if_past(dt_utc, client_now_utc)

    # Store naive UTC if DB column is timestamp without time zone.
    return dt_utc.replace(tzinfo=None) if dt_utc else None


def _make_failed_draft(now: datetime, error: Exception, content_item_id=None) -> ContentDraft:
    return ContentDraft(
        id=uuid.uuid4(),
        content_item_id=content_item_id,
        status="FAILED",
        last_error=str(error),
        updated_at=now,
    )


def _create_draft_from_generation(
    *,
    db: Session,
    now: datetime,
    result: dict,
    payload: GenerateDraftsRequest,
    content_item_id=None,
) -> ContentDraft:
    structured = result.get("structured") or {}
    caption = (result.get("body_text") or "").strip()
    hashtags = _normalize_hashtags(result, structured)
    scheduled_dt = _scheduled_dt_from_result(result, structured, payload.client_now)

    draft = ContentDraft(
        id=uuid.uuid4(),
        content_item_id=content_item_id,
        status="PENDING_APPROVAL",
        body_text=caption or None,
        hashtags=hashtags or None,
        scheduled_at=scheduled_dt,
        structured=structured or None,
        last_error=None,
        updated_at=now,
    )

    db.add(draft)
    return draft


def _generate_single_direct(payload: GenerateDraftsRequest, db: Session):
    """
    Temporary AI-chat/demo path.

    This does NOT use monthly planning and does NOT require TOPIC_INGESTED rows.
    It generates exactly one campaign draft from payload.topic, saves that draft,
    and returns it immediately so the frontend can render the canvas preview.
    """
    now = datetime.utcnow()
    topic_text = (payload.topic or "").strip()

    if not topic_text:
        return {
            "created": 0,
            "generated": 0,
            "failed": 1,
            "error": "topic is required when mode='single'",
        }

    platform = (payload.platforms or ["instagram"])[0]

    selected_tone = _pick_random_tone(
        db=db,
        requested_tone_id=payload.tone_id,
    )

    tone_name = getattr(selected_tone, "name", None)
    tone_label = getattr(selected_tone, "label", None)
    tone_description = getattr(selected_tone, "description", None)

    try:
        result = generate_post(
            topic_text=topic_text,
            platform=platform,
            brand_id=payload.brand_id,
            brand_profile_summary=payload.brand_profile_summary,
            brand_profile_json=payload.brand_profile_json,
            target_month=None,
            posts_per_week=1,
            client_now_utc_iso=payload.client_now,
            timezone=payload.timezone or "Europe/London",
            posting_hour_local=payload.posting_hour_local or 9,
            total_posts=1,
            post_index=0,
            tone_name=tone_name or payload.tone_name,
            tone_label=tone_label or payload.tone_label,
            tone_description=tone_description or payload.tone_description,
            tone_prompt_instruction=payload.tone_prompt_instruction,
            org_context_block=payload.org_context_block,
            org_structured_patch=payload.org_structured_patch,
        )

        draft = _create_draft_from_generation(
            db=db,
            now=now,
            result=result,
            payload=payload,
            content_item_id=None,
        )

        db.commit()

        return {
            "created": 1,
            "generated": 1,
            "failed": 0,
            "mode": "single",
            "draft_id": str(draft.id),
            "draft": {
                "id": str(draft.id),
                "platform": platform,
                "status": draft.status,
                "body_text": draft.body_text,
                "hashtags": draft.hashtags,
                "tone": {
                    "id": str(selected_tone.id) if selected_tone else None,
                    "name": tone_name,
                    "label": tone_label,
                    "description": tone_description,
                },
                "scheduled_at": draft.scheduled_at.isoformat() if draft.scheduled_at else None,
                "structured": draft.structured,
                "media_url": getattr(draft, "media_url", None),
            },
            "structured": draft.structured,
        }

    except Exception as e:
        db.rollback()

        try:
            db.add(_make_failed_draft(now, e, content_item_id=None))
            db.commit()
        except Exception:
            db.rollback()

        return {
            "created": 1,
            "generated": 0,
            "failed": 1,
            "mode": "single",
            "error": str(e),
        }


@router.post("/text")
def generate_drafts(payload: GenerateDraftsRequest, db: Session = Depends(get_db)):
    # New temporary AI chat/demo path.
    # This avoids all monthly calculations and creates exactly one draft.
    if payload.mode == "single":
        return _generate_single_direct(payload, db)

    now = datetime.utcnow()

    q = select(ContentItem).where(ContentItem.brand_id == payload.brand_id)

    if payload.platforms:
        q = q.where(ContentItem.platform.in_(payload.platforms))

    q = q.where(ContentItem.status == "TOPIC_INGESTED")

    if payload.mode == "monthly" and payload.target_month and hasattr(ContentItem, "plan_month"):
        q = q.where(ContentItem.plan_month == payload.target_month)

    items = db.execute(q).scalars().all()

    if not items:
        return {
            "created": 0,
            "generated": 0,
            "note": "No matching content_items found.",
        }

    generated = 0
    failed = 0

    for it in items:
        topic_text = (getattr(it, "topic", None) or "").strip() or "Untitled topic"

        selected_tone = _pick_random_tone(
            db=db,
            requested_tone_id=payload.tone_id,
        )

        tone_name = getattr(selected_tone, "name", None)
        tone_label = getattr(selected_tone, "label", None)
        tone_description = getattr(selected_tone, "description", None)

        try:
            result = generate_post(
                topic_text=topic_text,
                platform=it.platform,
                brand_id=payload.brand_id,
                brand_profile_summary=payload.brand_profile_summary,
                brand_profile_json=payload.brand_profile_json,
                target_month=payload.target_month,
                posts_per_week=payload.posts_per_week,
                client_now_utc_iso=payload.client_now,
                timezone=payload.timezone or "Europe/London",
                posting_hour_local=payload.posting_hour_local or 9,
                tone_name=tone_name or payload.tone_name,
                tone_label=tone_label or payload.tone_label,
                tone_description=tone_description or payload.tone_description,
                tone_prompt_instruction=payload.tone_prompt_instruction,
                org_context_block=payload.org_context_block,
                org_structured_patch=payload.org_structured_patch,
            )

            _create_draft_from_generation(
                db=db,
                now=now,
                result=result,
                payload=payload,
                content_item_id=it.id,
            )

            it.status = "HAS_DRAFT"
            it.updated_at = now

            generated += 1

        except Exception as e:
            failed += 1
            db.rollback()

            db.add(_make_failed_draft(now, e, content_item_id=getattr(it, "id", None)))

    db.commit()

    return {
        "created": len(items),
        "generated": generated,
        "failed": failed,
    }
