"""
Scheduling routes (same style as your /facebook router: SQLAlchemy Session + get_current_org).

    POST   /social/suggest-time      agent picks a post time
    POST   /social/schedule          uploads the image to Facebook and schedules it
    GET    /social/scheduled         queue
    DELETE /social/scheduled/{id}    cancel

Register in main.py:
    from app.routers import social
    app.include_router(social.router)
"""
from __future__ import annotations

import base64
import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.ai.post_time import suggest_post_time
from app.database import get_db
from app.dependencies.org import get_current_org
from app.models.facebook_page import FacebookPage
from app.models.organisation import Organisation
from app.services import fb_scheduler

router = APIRouter(prefix="/social", tags=["social"])


class SuggestReq(BaseModel):
    context: str = ""
    caption: str = ""
    timezone: str = "Africa/Blantyre"


@router.post("/suggest-time")
def suggest_time(p: SuggestReq, org: Organisation = Depends(get_current_org)):
    return suggest_post_time(p.context, p.caption, p.timezone)


class ScheduleReq(BaseModel):
    account_id: str            # facebook_pages.id
    image_base64: str          # data URL or raw base64 of the PNG
    caption: str = ""
    post_at_unix: int
    reason: str | None = None


@router.post("/schedule")
def schedule(p: ScheduleReq, org: Organisation = Depends(get_current_org), db: Session = Depends(get_db)):
    now = time.time()
    if p.post_at_unix < now + 15 * 60:
        raise HTTPException(400, "Pick a time at least 15 minutes from now.")
    if p.post_at_unix > now + 29 * 86400:
        raise HTTPException(400, "Facebook only allows scheduling up to 30 days ahead.")

    try:
        page_uuid = UUID(p.account_id)
    except ValueError:
        raise HTTPException(400, "Invalid page id.")

    page = db.execute(
        select(FacebookPage).where(FacebookPage.id == page_uuid, FacebookPage.org_id == org.id)
    ).scalars().first()
    if not page:
        raise HTTPException(404, "Facebook Page not found. Reconnect Facebook.")

    try:
        image_bytes = base64.b64decode(p.image_base64.split(",", 1)[-1])
    except Exception:
        raise HTTPException(400, "Invalid image.")

    try:
        fb_post_id = fb_scheduler.schedule_photo_post(
            page.facebook_page_id, page.access_token, image_bytes, p.caption, p.post_at_unix,
        )
    except Exception as e:
        print("[SCHEDULE] failed:", e)
        msg = "Facebook login expired. Please reconnect Facebook." if "code 190" in str(e) else str(e)
        raise HTTPException(502, msg)

    row = db.execute(
        text(
            """
            INSERT INTO scheduled_posts (org_id, page_row_id, caption, post_at, fb_post_id, reason)
            VALUES (:org, :page, :caption, to_timestamp(:ts), :fb, :reason)
            RETURNING id::text AS id, post_at
            """
        ),
        {"org": org.id, "page": page.id, "caption": p.caption, "ts": p.post_at_unix,
         "fb": fb_post_id, "reason": p.reason},
    ).mappings().first()
    db.commit()
    return {"id": row["id"], "fb_post_id": fb_post_id, "post_at": row["post_at"].isoformat()}


@router.get("/scheduled")
def scheduled(org: Organisation = Depends(get_current_org), db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            """
            SELECT s.id::text AS id, s.caption, s.post_at, s.status, s.reason, f.name AS page_name
            FROM scheduled_posts s JOIN facebook_pages f ON f.id = s.page_row_id
            WHERE s.org_id = :org ORDER BY s.post_at DESC LIMIT 50
            """
        ),
        {"org": org.id},
    ).mappings().all()

    now = datetime.now(timezone.utc)
    out = []
    for r in rows:
        item = dict(r)
        if item["status"] == "scheduled" and item["post_at"] <= now:
            item["status"] = "posted"
        item["post_at"] = item["post_at"].isoformat()
        out.append(item)
    return out


@router.delete("/scheduled/{post_id}")
def cancel(post_id: str, org: Organisation = Depends(get_current_org), db: Session = Depends(get_db)):
    row = db.execute(
        text(
            """
            SELECT s.fb_post_id, f.access_token
            FROM scheduled_posts s JOIN facebook_pages f ON f.id = s.page_row_id
            WHERE s.id = CAST(:id AS uuid) AND s.org_id = :org
              AND s.status = 'scheduled' AND s.post_at > now()
            """
        ),
        {"id": post_id, "org": org.id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "Nothing to cancel.")
    try:
        fb_scheduler.delete_post(row["fb_post_id"], row["access_token"])
    except Exception as e:
        print("[CANCEL] facebook delete failed:", e)
    db.execute(text("UPDATE scheduled_posts SET status = 'cancelled' WHERE id = CAST(:id AS uuid)"), {"id": post_id})
    db.commit()
    return {"ok": True}