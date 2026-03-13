import os
import httpx
from datetime import datetime
from typing import Any, Optional
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.content_item import ContentItem
from app.models.content_draft import ContentDraft
from app.services.state_machine import ensure_transition
from app.routers.content import _parse_media_urls

router = APIRouter(prefix="/make", tags=["make"])


def _parse_ids(payload: dict) -> list[str]:
    ids = payload.get("draft_ids") or payload.get("content_draft_ids") or payload.get("ids") or []
    if isinstance(ids, str):
        ids = [ids]
    if not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="draft_ids must be a list of strings")
    ids = [str(x).strip() for x in ids if str(x).strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="draft_ids is required")
    return ids


def _coerce_hashtag_list(hashtags: Any) -> list[str]:
    if not hashtags:
        return []
    if isinstance(hashtags, list):
        return [str(x).strip() for x in hashtags if str(x).strip()]
    s = str(hashtags).strip()
    if not s:
        return []
    parts = [p.strip() for p in s.replace("\n", " ").split(" ") if p.strip()]
    out = [p if p.startswith("#") else f"#{p}" for p in parts]
    return out


def _random_link(draft_id: str) -> Optional[str]:
    probability = float(os.getenv("LINK_PROBABILITY", "0.4"))
    if random.random() > probability:
        return None
    base = os.getenv("PUBLIC_SITE_BASE_URL", "https://neuroflowai.co.uk")
    return f"{base}/content/{draft_id}"


def _build_text(draft: ContentDraft) -> str:
    txt = (draft.body_text or "").strip()
    tags = _coerce_hashtag_list(draft.hashtags)
    if tags:
        if not any(t in txt for t in tags):
            txt = (txt + "\n\n" + " ".join(tags)).strip()
    return txt


@router.post("/publish")
def publish_via_make(payload: dict, db: Session = Depends(get_db)):
    """
    UI calls this to publish drafts via Make.
    Each draft is sent as a separate webhook call — Make does not
    support arrays, it processes one object per trigger.
    """

    print("publish_via_make payload:", payload)
    make_webhook_url = (os.getenv("MAKE_WEBHOOK_URL") or "").strip()
    make_api_key     = (os.getenv("MAKE_API_KEY") or "").strip()

    if not make_webhook_url:
        raise HTTPException(status_code=500, detail="MAKE_WEBHOOK_URL is not set in backend .env")
    if not make_api_key:
        raise HTTPException(status_code=500, detail="MAKE_API_KEY is not set in backend .env")

    draft_ids = _parse_ids(payload)

    rows = db.execute(
        select(ContentDraft).where(ContentDraft.id.in_(draft_ids))
    ).scalars().all()

    print("Publishing drafts via Make rows:", rows)

    if not rows:
        raise HTTPException(status_code=404, detail="No drafts found")

    to_send: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for draft in rows:
        platform = (getattr(draft, "platform", None) or "").lower().strip()

        text = _build_text(draft)
        if not text:
            skipped.append({
                "id": str(draft.id),
                "status": draft.status,
                "reason": "Empty body_text",
            })
            continue

        media_urls = _parse_media_urls(getattr(draft, "media_urls", None))
        media_url  = getattr(draft, "media_url", None)
        link       = _random_link(str(draft.id))

        to_send.append({
            "content_draft_id": str(draft.id),
            "link":             link,
            "content_item_id":  str(getattr(draft, "content_item_id", None))
                                if getattr(draft, "content_item_id", None) else None,
            "brand_id":         getattr(draft, "brand_id", None),
            "platform":         platform,
            "topic":            (getattr(draft, "structured", None) or {}).get("subheading"),
            "plan_month":       getattr(draft, "plan_month", None),
            "times_per_week":   getattr(draft, "times_per_week", None),
            "text":             text,
            "hashtags":         _coerce_hashtag_list(getattr(draft, "hashtags", None)),
            "hashtags_text":    " ".join(_coerce_hashtag_list(getattr(draft, "hashtags", None))) or None,
            "scheduled_at":     draft.scheduled_at.isoformat()
                                if getattr(draft, "scheduled_at", None) else None,
            "media_type":       getattr(draft, "media_type", None),
            "media_url":        media_url,
            "media_urls":       media_urls,
            "thumbnail_url":    getattr(draft, "thumbnail_url", None),
            "media_provider":   getattr(draft, "media_provider", None),
            "media_caption":    getattr(draft, "media_caption", None),
        })

    if not to_send:
        return {"sent": 0, "skipped": len(skipped), "skipped_items": skipped}

    headers = {
        "Content-Type": "application/json",
        "x-make-apikey": make_api_key,
    }
    print("webhook_url:", make_webhook_url)

    # ── Send one request per draft ────────────────────────────────────────────
    # Make webhooks process a single object per trigger — sending an array
    # causes Make to silently ignore all but the first item.
    make_status_codes: list[dict] = []
    failed_sends:      list[dict] = []

    try:
        with httpx.Client(timeout=90.0) as client:
            for item in to_send:
                draft_id = item["content_draft_id"]
                try:
                    r = client.post(make_webhook_url, json=item, headers=headers)
                    print(f"  Make → draft {draft_id}: HTTP {r.status_code}")
                    if r.status_code >= 400:
                        failed_sends.append({
                            "content_draft_id": draft_id,
                            "status_code":      r.status_code,
                            "detail":           r.text,
                        })
                    else:
                        make_status_codes.append({
                            "content_draft_id": draft_id,
                            "status_code":      r.status_code,
                        })
                except Exception as e:
                    print(f"  Make → draft {draft_id}: request failed — {e}")
                    failed_sends.append({
                        "content_draft_id": draft_id,
                        "error":            str(e),
                    })
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Make webhook: {e}")

    if failed_sends and not make_status_codes:
        # Every single request failed — hard error
        raise HTTPException(
            status_code=502,
            detail=f"All Make webhook calls failed: {failed_sends}",
        )

    # ── Mark successfully sent drafts as PUBLISHED ────────────────────────────
    sent_ids = {x["content_draft_id"] for x in make_status_codes}
    now      = datetime.utcnow()
    published = 0

    for draft in rows:
        if str(draft.id) not in sent_ids:
            continue

        try:
            ensure_transition(draft.status, "PUBLISHED")
        except Exception:
            pass

        draft.status       = "PUBLISHED"
        draft.published_at = now
        draft.last_error   = None
        draft.updated_at   = now

        if hasattr(draft, "attempt_count") and draft.attempt_count is not None:
            draft.attempt_count += 1

        published += 1

    db.commit()

    return {
        "sent":             len(make_status_codes),
        "skipped":          len(skipped),
        "skipped_items":    skipped,
        "published":        published,
        "failed_sends":     failed_sends,
        "make_status_codes": make_status_codes,
        "note": "Each draft was sent as a separate Make webhook trigger.",
    }