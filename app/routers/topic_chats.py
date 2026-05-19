from datetime import datetime, timezone
import uuid
import threading
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import select, delete
from fastapi import Query
from app.models.brand import Brand
from app.database import get_db, engine
from app.models.topic_chat import TopicChat
from app.models.content_draft import ContentDraft
from app.services.monthly_generator import generate_monthly_drafts
from app.utils.scheduling import posts_in_month
from app.dependencies.org import get_current_org
from app.models.organisation import Organisation
from typing import List

from app.models.tone import Tone

router = APIRouter(prefix="/topic-chats", tags=["topic-chats"])


class TopicChatPreviewRequest(BaseModel):
    brand_id: str
    topic: str
    mode: str | None = "monthly"
    target_month: str | None = None  # "YYYY-MM"
    posts_per_week: int | None = 1

class TopicChatBackgroundUpdate(BaseModel):
    background_images: List[str]

class TopicChatCreateRequest(TopicChatPreviewRequest):
    tone_id: str | None = None
    client_now: str | None = None
    timezone: str | None = "Europe/London"
    posting_hour_local: int | None = 9


@router.post("/preview")
def preview_count(payload: TopicChatPreviewRequest):
    if payload.mode == "single":
        return {"will_generate": 1}

    if not payload.target_month:
        raise HTTPException(status_code=422, detail="target_month is required unless mode='single'")

    n = posts_in_month(payload.target_month, payload.posts_per_week or 1)
    return {"will_generate": n}


def _resolve_target_month(payload: TopicChatCreateRequest) -> str:
    if payload.target_month:
        return payload.target_month

    now = datetime.now(timezone.utc)
    return f"{now.year}-{str(now.month).zfill(2)}"


# ── Background generation thread ──────────────────────────────────────────────

def _run_generation_in_background(
    chat_id: uuid.UUID,
    org_id: uuid.UUID,
    brand_id: str,
    tone_id: str | None,
    topic: str,
    mode: str | None,
    target_month: str | None,
    posts_per_week: int | None,
    brand_profile_summary: str | None,
    brand_profile_json: dict | None,
    tone_name: str | None,
    tone_label: str | None,
    tone_description: str | None,
    client_now: str | None,
    tz: str,
    posting_hour_local: int,
) -> None:
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db: Session = SessionLocal()
    try:
        res = generate_monthly_drafts(
            db=db,
            topic_chat_id=chat_id,
            org_id=org_id,
            brand_id=brand_id,
            tone_id=tone_id,
            topic=topic,
            mode=mode or "monthly",
            target_month=target_month,
            posts_per_week=posts_per_week or 1,
            brand_profile_summary=brand_profile_summary,
            brand_profile_json=brand_profile_json,
            tone_name=tone_name,
            tone_label=tone_label,
            tone_description=tone_description,
            client_now=client_now,
            timezone=tz,
            posting_hour_local=posting_hour_local,
        )
        print(f"[topic_chats] Background generation done: {res}")

        chat = db.execute(select(TopicChat).where(TopicChat.id == chat_id)).scalars().first()
        if chat:
            chat.generation_status = "done"
            chat.generation_result = res
            chat.updated_at        = datetime.now(timezone.utc)
            db.commit()

    except Exception as e:
        print(f"[topic_chats] Background generation FAILED: {e}")
        try:
            chat = db.execute(select(TopicChat).where(TopicChat.id == chat_id)).scalars().first()
            if chat:
                chat.generation_status = "failed"
                chat.generation_error  = str(e)[:500]
                chat.updated_at        = datetime.now(timezone.utc)
                db.commit()
        except Exception as inner:
            print(f"[topic_chats] Could not save error status: {inner}")
    finally:
        db.close()


# ── POST /topic-chats ─────────────────────────────────────────────────────────

@router.post("")
def create_topic_chat_and_generate(
    payload: TopicChatCreateRequest,
    org: Organisation = Depends(get_current_org),   # ← NEW
    db: Session = Depends(get_db),
):
    chat_id = uuid.uuid4()
    now     = datetime.now(timezone.utc)
    mode    = payload.mode or "monthly"

    # target_month is optional for AI-chat single generation.
    # Keep a harmless current-month value in the chat row for old UI compatibility.
    resolved_target_month = _resolve_target_month(payload)
    resolved_posts_per_week = 1 if mode == "single" else (payload.posts_per_week or 1)

    chat = TopicChat(
        id=chat_id,
        brand_id=payload.brand_id,
        tone_id=payload.tone_id,
        org_id=org.id,
        topic=payload.topic,
        target_month=resolved_target_month,
        posts_per_week=resolved_posts_per_week,
        generation_status="processing",
        created_at=now,
        updated_at=now,
    )
    db.add(chat)
    db.commit()

    brand_profile_summary: str | None = None
    brand_profile_json:    dict | None = None
    try:
        brandData = db.execute(
            select(Brand).where(
                Brand.id     == payload.brand_id,
                Brand.org_id == org.id,             # ← scoped
            )
        ).scalars().first()
        if brandData:
            brand_profile_summary = getattr(brandData, "profile_summary", None)
            brand_profile_json    = getattr(brandData, "profile_json",    None)
    except Exception as e:
        print(f"[topic_chats] Brand load warning (non-fatal): {e}")

    tone_name: str | None = None
    tone_label: str | None = None
    tone_description: str | None = None

    if payload.tone_id:
        try:
            tone = db.execute(
                select(Tone).where(Tone.id == payload.tone_id)
            ).scalars().first()

            if not tone:
                raise HTTPException(status_code=400, detail="Tone not found")

            tone_name = tone.name
            tone_label = tone.label
            tone_description = tone.description
        except HTTPException:
            raise
        except Exception as e:
            print(f"[topic_chats] Tone load warning (non-fatal): {e}")

    thread = threading.Thread(
        target=_run_generation_in_background,
        args=(
            chat_id,
            org.id,
            payload.brand_id,
            payload.tone_id,
            payload.topic,
            mode,
            resolved_target_month,
            resolved_posts_per_week,
            brand_profile_summary,
            brand_profile_json,
            tone_name,
            tone_label,
            tone_description,
            payload.client_now,
            payload.timezone or "Europe/London",
            payload.posting_hour_local or 9,
        ),
        daemon=True,
    )
    thread.start()

    return {
        "topic_chat_id": str(chat_id),
        "status":        "processing",
    }


# ── GET /{chat_id}/status ─────────────────────────────────────────────────────

@router.get("/{chat_id}/status")
def get_topic_chat_status(
    chat_id: str,
    org: Organisation = Depends(get_current_org),   # ← NEW
    db: Session = Depends(get_db),
):
    try:
        cid = uuid.UUID(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat id")

    chat = db.execute(
        select(TopicChat).where(
            TopicChat.id     == cid,
            TopicChat.org_id == org.id,             # ← scoped
        )
    ).scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Topic chat not found")

    status = getattr(chat, "generation_status", None) or "done"

    if status == "done":
        result = getattr(chat, "generation_result", None) or {}
        return {
            "status":    "done",
            "generated": result.get("generated", 0) if isinstance(result, dict) else 0,
            "failed":    result.get("failed",    0) if isinstance(result, dict) else 0,
        }
    elif status == "failed":
        return {
            "status": "failed",
            "error":  getattr(chat, "generation_error", "Unknown error"),
        }
    else:
        count = db.execute(
            select(ContentDraft).where(ContentDraft.topic_chat_id == cid)
        ).scalars().all()
        return {
            "status":        "processing",
            "drafts_so_far": len(count),
        }


# ── GET /{chat_id} ────────────────────────────────────────────────────────────

@router.get("/{chat_id}")
def get_topic_chat(
    chat_id: str,
    org: Organisation = Depends(get_current_org),   # ← NEW
    db: Session = Depends(get_db),
):
    try:
        cid = uuid.UUID(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat id")

    chat = db.execute(
        select(TopicChat).where(
            TopicChat.id     == cid,
            TopicChat.org_id == org.id,             # ← scoped
        )
    ).scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Topic chat not found")

    return {
        "id": str(chat.id),
        "brand_id": chat.brand_id,
        "topic": chat.topic,
        "org_slug": org.slug,
        "background_images": chat.background_images,
        "target_month": chat.target_month,
        "posts_per_week": chat.posts_per_week,
        "created_at": chat.created_at.isoformat() if chat.created_at else None,
        "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
    }


# ── GET /{chat_id}/drafts ─────────────────────────────────────────────────────

@router.get("/{chat_id}/drafts")
def list_chat_drafts(
    chat_id: str,
    org: Organisation = Depends(get_current_org),   # ← NEW
    db: Session = Depends(get_db),
):
    try:
        cid = uuid.UUID(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat id")

    # Verify chat belongs to this org first
    chat = db.execute(
        select(TopicChat).where(
            TopicChat.id     == cid,
            TopicChat.org_id == org.id,             # ← scoped
        )
    ).scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Topic chat not found")

    rows = db.execute(
        select(ContentDraft)
        .where(ContentDraft.topic_chat_id == cid)
        .order_by(
            ContentDraft.scheduled_at.asc().nulls_last(),
            ContentDraft.created_at.asc()
        )
    ).scalars().all()

    def parse_media_urls(v):
        if not v:
            return []
        if isinstance(v, list):
            return v
        try:
            import json
            parsed = json.loads(v)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []

    return [
        {
            "id": str(d.id),
            "topic_chat_id": str(d.topic_chat_id),
            "brand_id": d.brand_id,
            "platform": d.platform,
            "status": d.status,
            "org_slug": org.slug,
            "body_text": d.body_text,
            "hashtags": d.hashtags,
            "structured": d.structured,
            "scheduled_at": d.scheduled_at.isoformat() if d.scheduled_at else None,
            "media_type": d.media_type,
            "media_url": d.media_url,
            "media_urls": parse_media_urls(d.media_urls),
            "thumbnail_url": d.thumbnail_url,
            "media_provider": d.media_provider,
            "media_caption": d.media_caption,
            "last_error": d.last_error,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        }
        for d in rows
    ]


# ── POST /{chat_id}/regenerate ────────────────────────────────────────────────

@router.post("/{chat_id}/regenerate")
def regenerate(
    chat_id: str,
    payload: dict,
    org: Organisation = Depends(get_current_org),   # ← NEW
    db: Session = Depends(get_db),
):
    try:
        cid = uuid.UUID(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat id")

    chat = db.execute(
        select(TopicChat).where(
            TopicChat.id     == cid,
            TopicChat.org_id == org.id,             # ← scoped
        )
    ).scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Topic chat not found")

    res = generate_monthly_drafts(
        db=db,
        topic_chat_id=cid,
        org_id=org.id,                              # ← NEW
        brand_id=chat.brand_id,
        topic=chat.topic,
        target_month=chat.target_month,
        posts_per_week=chat.posts_per_week,
        brand_profile_summary=payload.get("brand_profile_summary"),
        brand_profile_json=payload.get("brand_profile_json"),
        client_now=payload.get("client_now"),
        timezone=payload.get("timezone") or "Europe/London",
        posting_hour_local=payload.get("posting_hour_local") or 9,
    )
    return res


# ── GET "" — list topic chats ─────────────────────────────────────────────────

@router.get("")
def list_topic_chats(
    limit: int = Query(50, ge=1, le=500),
    org: Organisation = Depends(get_current_org),   # ← NEW
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(TopicChat)
        .where(TopicChat.org_id == org.id)          # ← scoped
        .order_by(TopicChat.created_at.desc())
        .limit(limit)
    ).scalars().all()

    return [{
        "id": str(c.id),
        "brand_id": c.brand_id,
        "topic": c.topic,
        "target_month": c.target_month,
        "background_images": c.background_images or [],
        "posts_per_week": c.posts_per_week,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    } for c in rows]


# ── PATCH /{topic_chat_id}/backgrounds ───────────────────────────────────────

@router.patch("/{topic_chat_id}/backgrounds")
def update_topic_chat_backgrounds(
    topic_chat_id: str,
    payload: TopicChatBackgroundUpdate,
    org: Organisation = Depends(get_current_org),   # ← NEW
    db: Session = Depends(get_db),
):
    chat = db.execute(
        select(TopicChat).where(
            TopicChat.id     == topic_chat_id,
            TopicChat.org_id == org.id,             # ← scoped
        )
    ).scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Topic chat not found")

    existing = chat.background_images or []
    merged   = list(dict.fromkeys(existing + payload.background_images))

    chat.background_images = merged
    db.commit()

    return {
        "ok":               True,
        "count":            len(merged),
        "background_images": merged,
    }


# ── DELETE /{topic_chat_id} ───────────────────────────────────────────────────

@router.delete("/{topic_chat_id}")
def delete_topic_chat(
    topic_chat_id: str,
    org: Organisation = Depends(get_current_org),   # ← NEW
    db: Session = Depends(get_db),
):
    try:
        parsed_id = uuid.UUID(topic_chat_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid topic_chat_id format")

    chat = db.execute(
        select(TopicChat).where(
            TopicChat.id     == parsed_id,
            TopicChat.org_id == org.id,             # ← scoped
        )
    ).scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Topic chat not found")

    db.execute(delete(ContentDraft).where(ContentDraft.topic_chat_id == parsed_id))
    db.delete(chat)
    db.commit()

    return {"ok": True, "id": topic_chat_id}