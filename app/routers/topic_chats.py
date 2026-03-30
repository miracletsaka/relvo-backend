from datetime import datetime, timezone
import uuid
import threading
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import select
from sqlalchemy import delete
from fastapi import Query
from app.models.brand import Brand
from app.database import get_db, engine   # make sure engine is exported from app.database
from app.models.topic_chat import TopicChat
from app.models.content_draft import ContentDraft
from app.services.monthly_generator import generate_monthly_drafts
from app.utils.scheduling import posts_in_month
from typing import List

router = APIRouter(prefix="/topic-chats", tags=["topic-chats"])

class TopicChatPreviewRequest(BaseModel):
    brand_id: str
    topic: str
    target_month: str  # "YYYY-MM"
    posts_per_week: int

class TopicChatBackgroundUpdate(BaseModel):
    background_images: List[str]

@router.post("/preview")
def preview_count(payload: TopicChatPreviewRequest):
    n = posts_in_month(payload.target_month, payload.posts_per_week)
    return {"will_generate": n}

class TopicChatCreateRequest(TopicChatPreviewRequest):
    client_now: str | None = None
    timezone: str | None = "Europe/London"
    posting_hour_local: int | None = 9


# ── Background generation thread ──────────────────────────────────────────────
# Runs independently after POST returns. Uses its own DB session so it never
# touches the request session which is already closed by then.

def _run_generation_in_background(
    chat_id:              uuid.UUID,
    brand_id:             str,
    topic:                str,
    target_month:         str,
    posts_per_week:       int,
    brand_profile_summary: str | None,
    brand_profile_json:   dict | None,
    client_now:           str | None,
    tz:                   str,
    posting_hour_local:   int,
) -> None:
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db: Session = SessionLocal()
    try:
        res = generate_monthly_drafts(
            db=db,
            topic_chat_id=chat_id,
            brand_id=brand_id,
            topic=topic,
            target_month=target_month,
            posts_per_week=posts_per_week,
            brand_profile_summary=brand_profile_summary,
            brand_profile_json=brand_profile_json,
            client_now=client_now,
            timezone=tz,
            posting_hour_local=posting_hour_local,
        )
        print(f"[topic_chats] Background generation done: {res}")

        # Mark as done
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


# ── POST /topic-chats — returns instantly ─────────────────────────────────────

@router.post("")
def create_topic_chat_and_generate(
    payload: TopicChatCreateRequest,
    db: Session = Depends(get_db),
):
    # 1) Create the TopicChat row immediately — client gets ID in < 1s
    chat_id = uuid.uuid4()
    now     = datetime.now(timezone.utc)

    chat = TopicChat(
        id=chat_id,
        brand_id=payload.brand_id,
        topic=payload.topic,
        target_month=payload.target_month,
        posts_per_week=payload.posts_per_week,
        generation_status="processing",
        created_at=now,
        updated_at=now,
    )
    db.add(chat)
    db.commit()   # commit before spawning thread so row is visible immediately

    # 2) Load brand profile (fast — one DB read)
    brand_profile_summary: str | None = None
    brand_profile_json:    dict | None = None
    try:
        brandData = db.execute(
            select(Brand).where(Brand.id == payload.brand_id)
        ).scalars().first()
        if brandData:
            brand_profile_summary = getattr(brandData, "profile_summary", None)
            brand_profile_json    = getattr(brandData, "profile_json",    None)
    except Exception as e:
        print(f"[topic_chats] Brand load warning (non-fatal): {e}")

    # 3) Fire generation in background daemon thread — do NOT await
    thread = threading.Thread(
        target=_run_generation_in_background,
        args=(
            chat_id, payload.brand_id, payload.topic,
            payload.target_month, payload.posts_per_week,
            brand_profile_summary, brand_profile_json,
            payload.client_now,
            payload.timezone or "Europe/London",
            payload.posting_hour_local or 9,
        ),
        daemon=True,
    )
    thread.start()

    # Return immediately — frontend polls /status
    return {
        "topic_chat_id": str(chat_id),
        "status":        "processing",
    }


# ── GET /topic-chats/{id}/status — polling endpoint ──────────────────────────

@router.get("/{chat_id}/status")
def get_topic_chat_status(chat_id: str, db: Session = Depends(get_db)):
    """
    Frontend polls this every 4s.
    Returns:
      { status: "processing", drafts_so_far: N }
      { status: "done", generated: N, failed: N }
      { status: "failed", error: "..." }
    """
    try:
        cid = uuid.UUID(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat id")

    chat = db.execute(select(TopicChat).where(TopicChat.id == cid)).scalars().first()
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
        # Count drafts written so far — gives frontend a live progress number
        count = db.execute(
            select(ContentDraft).where(ContentDraft.topic_chat_id == cid)
        ).scalars().all()
        return {
            "status":        "processing",
            "drafts_so_far": len(count),
        }


# ── All existing routes below — unchanged ────────────────────────────────────

@router.get("/{chat_id}")
def get_topic_chat(chat_id: str, db: Session = Depends(get_db)):
    try:
        cid = uuid.UUID(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat id")

    chat = db.execute(select(TopicChat).where(TopicChat.id == cid)).scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Topic chat not found")

    return {
        "id": str(chat.id),
        "brand_id": chat.brand_id,
        "topic": chat.topic,
        "background_images": chat.background_images,
        "target_month": chat.target_month,
        "posts_per_week": chat.posts_per_week,
        "created_at": chat.created_at.isoformat() if chat.created_at else None,
        "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
    }

@router.get("/{chat_id}/drafts")
def list_chat_drafts(chat_id: str, db: Session = Depends(get_db)):
    try:
        cid = uuid.UUID(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat id")

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

@router.post("/{chat_id}/regenerate")
def regenerate(chat_id: str, payload: dict, db: Session = Depends(get_db)):
    try:
        cid = uuid.UUID(chat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat id")

    chat = db.execute(select(TopicChat).where(TopicChat.id == cid)).scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Topic chat not found")

    res = generate_monthly_drafts(
        db=db,
        topic_chat_id=cid,
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

@router.get("")
def list_topic_chats(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    rows = db.execute(
        select(TopicChat).order_by(TopicChat.created_at.desc()).limit(limit)
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

@router.patch("/{topic_chat_id}/backgrounds")
def update_topic_chat_backgrounds(
    topic_chat_id: str,
    payload: TopicChatBackgroundUpdate,
    db: Session = Depends(get_db),
):
    chat = db.query(TopicChat).filter(TopicChat.id == topic_chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Topic chat not found")

    existing = chat.background_images or []
    merged = list(dict.fromkeys(existing + payload.background_images))

    chat.background_images = merged
    db.commit()

    return {
        "ok": True,
        "count": len(merged),
        "background_images": merged,
    }

@router.delete("/{topic_chat_id}")
def delete_topic_chat(topic_chat_id: str, db: Session = Depends(get_db)):
    try:
        parsed_id = uuid.UUID(topic_chat_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid topic_chat_id format")

    chat = db.execute(
        select(TopicChat).where(TopicChat.id == parsed_id)
    ).scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Topic chat not found")

    db.execute(delete(ContentDraft).where(ContentDraft.topic_chat_id == parsed_id))
    db.delete(chat)
    db.commit()

    return {"ok": True, "id": topic_chat_id}