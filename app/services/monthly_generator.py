"""
app/services/generate_monthly_drafts.py
"""
from __future__ import annotations

import uuid
import math
import calendar
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.platform import Platform
from app.models.topic_chat import TopicChat
from app.models.content_draft import ContentDraft
from app.services.ai_generator import generate_post
from app.services.org_data_loader import load_org_context


def _build_platform_day_offsets(platforms: list) -> dict[str, int]:
    """
    Each platform gets a different weekday starting offset (0, 1, 2, 3...).
    Sorted alphabetically so order is deterministic.
    facebook=0 (Mon), instagram=1 (Tue), linkedin=2 (Wed), youtube=3 (Thu)
    """
    sorted_ids = sorted(p.id for p in platforms)
    return {pid: i for i, pid in enumerate(sorted_ids)}


def _remaining_weeks_in_month(
    year: int,
    month: int,
    now_utc: datetime,
    tz: ZoneInfo,
) -> float:
    now_local    = now_utc.astimezone(tz)
    days_in_m    = calendar.monthrange(year, month)[1]
    end_of_month = datetime(year, month, days_in_m, 23, 59, 59, tzinfo=tz)

    if now_local > end_of_month:
        return 0.0

    today_local    = now_local.date()
    end_date       = end_of_month.date()
    remaining_days = (end_date - today_local).days + 1
    return remaining_days / 7.0


def _compute_slots_for_platform(
    year: int,
    month: int,
    now_utc: datetime,
    tz: ZoneInfo,
    posting_hour_local: int,
    platform_id: str,
    n_posts: int,
    platform_offsets: dict[str, int],
) -> list[str]:
    """
    Returns exactly n_posts ISO-8601 UTC timestamps for one platform.
    Each platform starts from a different weekday (day offset) so posts
    never all land on the same day.
    """
    day_offset = platform_offsets.get(platform_id.lower(), 0)
    days_in_m  = calendar.monthrange(year, month)[1]
    min_future = now_utc + timedelta(minutes=30)

    # Build all available weekday slots for this month
    available: list[datetime] = []
    for day in range(1, days_in_m + 1):
        local_dt = datetime(year, month, day, posting_hour_local, 0, 0, tzinfo=tz)
        utc_dt   = local_dt.astimezone(ZoneInfo("UTC"))
        if local_dt.weekday() > 4:    # skip Sat/Sun
            continue
        if utc_dt <= min_future:      # skip past/near-future
            continue
        available.append(utc_dt)

    if not available:
        # Fallback: next n_posts weekdays from now
        cursor = now_utc + timedelta(hours=1)
        while len(available) < n_posts:
            local_c = cursor.astimezone(tz)
            if local_c.weekday() <= 4:
                slot = datetime(
                    local_c.year, local_c.month, local_c.day,
                    posting_hour_local, 0, 0, tzinfo=tz
                )
                available.append(slot.astimezone(ZoneInfo("UTC")))
            cursor += timedelta(days=1)

    # Apply day offset — rotate the list so each platform starts
    # on a different weekday. offset=0 → starts Mon, offset=1 → starts Tue, etc.
    if day_offset > 0 and len(available) > day_offset:
        available = available[day_offset:] + available[:day_offset]

    # Spread n_posts evenly across available slots
    if len(available) >= n_posts:
        step   = len(available) / n_posts
        chosen = [available[int(i * step)] for i in range(n_posts)]
    else:
        chosen = list(available)
        # Extend into next month if needed
        cursor_date = datetime(year, month, days_in_m, tzinfo=tz) + timedelta(days=1)
        while len(chosen) < n_posts:
            local_dt = datetime(
                cursor_date.year, cursor_date.month, cursor_date.day,
                posting_hour_local, 0, 0, tzinfo=tz
            )
            if local_dt.weekday() <= 4:
                chosen.append(local_dt.astimezone(ZoneInfo("UTC")))
            cursor_date += timedelta(days=1)

    chosen.sort()
    return [dt.strftime("%Y-%m-%dT%H:%M:%SZ") for dt in chosen[:n_posts]]


def _posts_for_platform(
    year: int,
    month: int,
    now_utc: datetime,
    tz: ZoneInfo,
    posts_per_week: int,
) -> int:
    weeks = _remaining_weeks_in_month(year, month, now_utc, tz)
    if weeks <= 0:
        return 0
    return max(1, math.ceil(posts_per_week * weeks))


def generate_monthly_drafts(
    *,
    db: Session,
    topic_chat_id: uuid.UUID,
    org_id: uuid.UUID,
    brand_id: str,
    tone_id: str | None = None,
    topic: str,
    mode: str = "monthly",
    target_month: str | None = None,
    posts_per_week: int = 1,
    brand_profile_summary: str | None = None,
    brand_profile_json: dict | None = None,
    tone_name: str | None = None,
    tone_label: str | None = None,
    tone_description: str | None = None,
    client_now: str | None = None,
    timezone: str = "Europe/London",
    posting_hour_local: int = 9,
) -> dict:

    # ── 1) Resolve timezone ───────────────────────────────────────────────────
    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, Exception):
        tz = ZoneInfo("Europe/London")

    single_mode = (mode or "").strip().lower() == "single"

    # ── 2) Parse target month ─────────────────────────────────────────────────
    try:
        target_month_safe = target_month or ""
        year  = int(target_month_safe[:4])
        month = int(target_month_safe[5:7])
    except Exception:
        now_local = datetime.now(tz)
        year, month = now_local.year, now_local.month

    # ── 3) Resolve "now" ──────────────────────────────────────────────────────
    if client_now:
        try:
            now_utc = datetime.fromisoformat(client_now.replace("Z", "+00:00"))
            if now_utc.tzinfo is None:
                now_utc = now_utc.replace(tzinfo=ZoneInfo("UTC"))
        except Exception:
            now_utc = datetime.now(ZoneInfo("UTC"))
    else:
        now_utc = datetime.now(ZoneInfo("UTC"))

    # ── 4) Load active platforms ──────────────────────────────────────────────
        # ── 4) Load active platforms ──────────────────────────────────────────────
    platforms = db.execute(
        select(Platform).where(
            Platform.is_active == True,
            Platform.org_id == org_id,
        )
    ).scalars().all()

    # If org has no active platforms, ensure a default Facebook platform exists
    if not platforms:
        facebook = db.execute(
            select(Platform).where(
                Platform.id == "facebook",
                Platform.org_id == org_id,
            )
        ).scalar_one_or_none()

        if not facebook:
            facebook = Platform(
                id="facebook",
                display_name="Facebook",
                is_active=True,
                org_id=org_id,
                created_at=datetime.now(),
            )
            db.add(facebook)
            db.commit()
            db.refresh(facebook)

        platforms = [facebook]

    if single_mode:
        # AI-chat demo: generate exactly one draft only.
        # Prefer Instagram when available because this flow previews one visual poster.
        preferred = next((p for p in platforms if str(p.id).lower() == "instagram"), None)
        platforms = [preferred or platforms[0]]

    platform_offsets = _build_platform_day_offsets(platforms)
    print(f"[generate_monthly_drafts] Platform day offsets: {platform_offsets}")

    # ── 5) Verify topic chat exists ───────────────────────────────────────────
    chat = db.execute(
        select(TopicChat).where(TopicChat.id == topic_chat_id)
    ).scalars().first()
    if not chat:
        raise ValueError("TopicChat not found")

    db_now          = datetime.now(ZoneInfo("UTC"))
    total_created   = 0
    total_generated = 0
    total_failed    = 0
    platform_summary: list[dict] = []

    # ── 6) Per-platform generation ────────────────────────────────────────────
    for platform in platforms:
        plat_id = platform.id

        if single_mode:
            n_posts = 1
            base_slot = now_utc + timedelta(hours=1)
            slots = [base_slot.replace(second=0, microsecond=0).isoformat().replace("+00:00", "Z")]
        else:
            n_posts = _posts_for_platform(year, month, now_utc, tz, posts_per_week)
            if n_posts == 0:
                platform_summary.append({
                    "platform": plat_id, "posts": 0,
                    "reason": "No remaining time in month",
                })
                continue

            slots = _compute_slots_for_platform(
                year=year,
                month=month,
                now_utc=now_utc,
                tz=tz,
                posting_hour_local=posting_hour_local,
                platform_id=plat_id,
                n_posts=n_posts,
                platform_offsets=platform_offsets,
            )

        print(f"[generate_monthly_drafts] Platform={plat_id} n_posts={n_posts} slots={slots}")

        plat_generated = 0
        plat_failed    = 0

            # ── 4.1) Load real org context once ─────────────────────────────────────
        org_ctx = load_org_context(db, org_id)
        org_context_block = org_ctx.to_ai_context_block()
        org_structured_patch = org_ctx.to_structured_patch()

        for i, slot in enumerate(slots):
            print(f"  [{plat_id}] Post {i+1}/{n_posts} → slot {slot}")
            try:
                result = generate_post(
                    topic_text=topic,
                    platform=plat_id,
                    brand_id=brand_id,
                    brand_profile_summary=brand_profile_summary,
                    brand_profile_json=brand_profile_json,
                    target_month=target_month or f"{year}-{str(month).zfill(2)}",
                    posts_per_week=posts_per_week or 1,
                    client_now_utc_iso=client_now,
                    timezone=timezone,
                    posting_hour_local=posting_hour_local,
                    post_index=i,
                    total_posts=n_posts,
                    assigned_slot=slot,
                    tone_name=tone_name,
                    tone_label=tone_label,
                    tone_description=tone_description,
                    tone_prompt_instruction=tone_description,
                    org_context_block=org_context_block,
                    org_structured_patch=org_structured_patch,
                )

                caption = (result.get("body_text") or "").strip() or None

                h = result.get("hashtags") or ""
                if isinstance(h, list):
                    hashtags = " ".join(str(x).strip() for x in h if str(x).strip()).strip() or None
                else:
                    hashtags = str(h).strip() or None

                structured   = result.get("structured") or {}
                scheduled_at = None
                try:
                    scheduled_at = datetime.fromisoformat(
                        slot.replace("Z", "+00:00")
                    )
                except Exception:
                    pass

                draft = ContentDraft(
                    id=uuid.uuid4(),
                    org_id=org_id,
                    topic_chat_id=topic_chat_id,
                    brand_id=brand_id,
                    tone_id=tone_id,
                    platform=plat_id,
                    status="PENDING_APPROVAL",
                    body_text=caption,
                    hashtags=hashtags,
                    scheduled_at=scheduled_at,
                    structured=structured or None,
                    last_error=None,
                    created_at=db_now,
                    updated_at=db_now,
                )
                db.add(draft)
                plat_generated += 1

            except Exception as e:
                import traceback
                print(f"  [{plat_id}] Post {i+1} FAILED: {e}")
                print(traceback.format_exc())
                db.add(ContentDraft(
                    id=uuid.uuid4(),
                    org_id=org_id,
                    topic_chat_id=topic_chat_id,
                    brand_id=brand_id,
                    tone_id=tone_id,
                    platform=plat_id,
                    status="FAILED",
                    last_error=str(e),
                    created_at=db_now,
                    updated_at=db_now,
                ))
                plat_failed += 1

        db.commit()

        total_created   += n_posts
        total_generated += plat_generated
        total_failed    += plat_failed

        platform_summary.append({
            "platform":  plat_id,
            "posts":     n_posts,
            "generated": plat_generated,
            "failed":    plat_failed,
            "slots":     slots,
        })

    return {
        "created":         total_created,
        "generated":       total_generated,
        "failed":          total_failed,
        "platforms":       platform_summary,
        "weeks_remaining": 0 if single_mode else round(_remaining_weeks_in_month(year, month, now_utc, tz), 2),
    }