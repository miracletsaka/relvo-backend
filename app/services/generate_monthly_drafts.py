"""
app/services/generate_monthly_drafts.py
───────────────────────────────────────
V3 — Correct per-platform draft generation with proper scheduling.

Key fixes vs V2:
  1. posts_per_week × remaining_weeks calculated PER PLATFORM independently.
  2. "Remaining weeks" = weeks left in the month from today (not full month).
  3. Each platform gets its OWN evenly-distributed schedule slots — no overlaps.
  4. Slots are spread across weekdays with a per-platform time offset so
     Facebook posts at 09:00, LinkedIn at 10:00, Instagram at 11:00, etc.
     This prevents two platforms ever posting at the exact same timestamp.
  5. ai_generator.generate_post is called with pre-assigned slot index
     so the model never picks the scheduling — Python owns it 100%.
"""
from __future__ import annotations

import uuid
import math
import calendar
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.platform import Platform
from app.models.topic_chat import TopicChat
from app.models.content_draft import ContentDraft
from app.services.ai_generator import generate_post


def _build_platform_offsets(platforms: list) -> dict[str, int]:
    """
    Derive per-platform minute offsets from the live platforms list.
    Platforms are sorted by their id (alphabetical) so the order is
    deterministic regardless of DB insertion order.
    Each platform gets a 30-minute stagger: index 0 → +0 min,
    index 1 → +30 min, index 2 → +60 min, etc.
    This guarantees no two platforms ever post at the same timestamp.
    """
    sorted_ids = sorted(p.id for p in platforms)
    return {pid: i * 30 for i, pid in enumerate(sorted_ids)}


def _platform_offset_minutes(platform_id: str, offsets: dict[str, int]) -> int:
    """Return minute offset for a platform from the computed offsets map."""
    return offsets.get(platform_id.lower(), 0)


# ── Core scheduler ────────────────────────────────────────────────────────────

def _remaining_weeks_in_month(
    year: int,
    month: int,
    now_utc: datetime,
    tz: ZoneInfo,
) -> float:
    """
    Return the number of weeks remaining in `year/month` from now_utc.
    Counts full 7-day blocks from today (inclusive) to end of month.
    Minimum returned value: 0.0  (if month is over).
    """
    now_local   = now_utc.astimezone(tz)
    days_in_m   = calendar.monthrange(year, month)[1]
    end_of_month = datetime(year, month, days_in_m, 23, 59, 59, tzinfo=tz)

    if now_local > end_of_month:
        return 0.0

    # Count remaining calendar days INCLUDING today
    today_local = now_local.date()
    end_date    = end_of_month.date()
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
    Returns exactly `n_posts` ISO-8601 UTC timestamps for one platform.

    Rules:
    - Only weekdays (Mon–Fri).
    - Must be at least 2 hours in the future.
    - Platform gets a fixed minute offset so posts from different platforms
      never land at the same time on the same day.
    - Posts are spread as evenly as possible across available days.
    - If there are fewer available days than posts, we stack (2 per day max,
      morning + afternoon), then fall back to next-month days.
    """
    offset_min = _platform_offset_minutes(platform_id, platform_offsets)
    post_hour  = posting_hour_local + (offset_min // 60)
    post_min   = offset_min % 60

    days_in_m  = calendar.monthrange(year, month)[1]
    min_future = now_utc + timedelta(hours=2)

    # Build all available weekday slots in the month
    available: list[datetime] = []
    for day in range(1, days_in_m + 1):
        local_dt = datetime(year, month, day, post_hour % 24, post_min, 0, tzinfo=tz)
        utc_dt   = local_dt.astimezone(ZoneInfo("UTC"))
        if local_dt.weekday() > 4:   # skip Sat/Sun
            continue
        if utc_dt <= min_future:     # skip past / near-future
            continue
        available.append(utc_dt)

    # If we have enough days, spread evenly
    if len(available) >= n_posts:
        step   = len(available) / n_posts
        chosen = [available[int(i * step)] for i in range(n_posts)]
        return [dt.strftime("%Y-%m-%dT%H:%M:%SZ") for dt in chosen]

    # Not enough days — use all available, then add afternoon slots (same days)
    chosen = list(available)
    if len(chosen) < n_posts:
        # Add afternoon slots (+6h) on available days
        for day_slot in available:
            if len(chosen) >= n_posts:
                break
            afternoon = day_slot + timedelta(hours=6)
            if afternoon not in chosen:
                chosen.append(afternoon)
        chosen.sort()

    # Still not enough — extend into next month
    cursor_date = datetime(year, month, days_in_m, tzinfo=tz) + timedelta(days=1)
    while len(chosen) < n_posts:
        local_dt = datetime(
            cursor_date.year, cursor_date.month, cursor_date.day,
            post_hour % 24, post_min, 0, tzinfo=tz
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
    """
    How many posts should we generate for this platform this month?
    = posts_per_week × remaining_weeks, rounded up, minimum 1.
    """
    weeks = _remaining_weeks_in_month(year, month, now_utc, tz)
    if weeks <= 0:
        return 0
    return max(1, math.ceil(posts_per_week * weeks))


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_monthly_drafts(
    *,
    db: Session,
    topic_chat_id: uuid.UUID,
    brand_id: str,
    topic: str,
    target_month: str,          # "YYYY-MM"
    posts_per_week: int,
    brand_profile_summary: str | None = None,
    brand_profile_json: dict | None = None,
    client_now: str | None = None,       # ISO-8601 from browser clock
    timezone: str = "Europe/London",
    posting_hour_local: int = 9,
) -> dict:
    """
    Generate ContentDraft rows for all active platforms.

    Per-platform logic:
      - Calculate remaining weeks in target_month from NOW.
      - n_posts = ceil(posts_per_week × remaining_weeks), min 1.
      - Compute n_posts evenly-spaced weekday slots for that platform.
      - Call ai_generator.generate_post once per slot, passing the
        pre-assigned slot so the model never does scheduling math.

    Example:
      2 weeks left, 1 post/week, 3 platforms
      → 2 posts × 3 platforms = 6 drafts total.
    """

    # ── 1) Resolve timezone ───────────────────────────────────────────────────
    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, Exception):
        tz = ZoneInfo("Europe/London")

    # ── 2) Parse target month ─────────────────────────────────────────────────
    try:
        year  = int(target_month[:4])
        month = int(target_month[5:7])
    except Exception:
        now_local = datetime.now(tz)
        year, month = now_local.year, now_local.month

    # ── 3) Resolve "now" ──────────────────────────────────────────────────────
    if client_now:
        try:
            now_utc = datetime.fromisoformat(client_now.replace("Z", "+00:00"))
        except Exception:
            now_utc = datetime.now(timezone.utc)
    else:
        now_utc = datetime.now(timezone.utc)

    # ── 4) Load active platforms ──────────────────────────────────────────────
    platforms = db.execute(
        select(Platform).where(Platform.is_active == True)
    ).scalars().all()

    if not platforms:
        return {
            "created": 0, "generated": 0, "failed": 0,
            "note": "No active platforms configured.",
        }

    # Build stagger offsets from the live platform list — no hardcoding
    platform_offsets = _build_platform_offsets(platforms)
    print(f"[generate_monthly_drafts] Platform offsets (minutes): {platform_offsets}")

    # ── 5) Verify topic chat exists ───────────────────────────────────────────
    chat = db.execute(
        select(TopicChat).where(TopicChat.id == topic_chat_id)
    ).scalars().first()
    if not chat:
        raise ValueError("TopicChat not found")

    db_now = datetime.now(timezone.utc)
    total_created = 0
    total_generated = 0
    total_failed = 0
    platform_summary: list[dict] = []

    # ── 6) Per-platform generation ────────────────────────────────────────────
    for platform in platforms:
        plat_id = platform.id   # e.g. "facebook", "linkedin"

        # How many posts for this platform this month?
        n_posts = _posts_for_platform(year, month, now_utc, tz, posts_per_week)

        if n_posts == 0:
            platform_summary.append({
                "platform": plat_id, "posts": 0,
                "reason": "No remaining time in month",
            })
            continue

        # Compute dedicated slots for this platform
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

        print(
            f"[generate_monthly_drafts] Platform={plat_id} "
            f"n_posts={n_posts} slots={slots}"
        )

        plat_generated = 0
        plat_failed    = 0

        for i, slot in enumerate(slots):
            print(
                f"  [{plat_id}] Post {i+1}/{n_posts} "
                f"→ slot {slot}"
            )
            try:
                result = generate_post(
                    topic_text=topic,
                    platform=plat_id,
                    brand_id=brand_id,
                    brand_profile_summary=brand_profile_summary,
                    brand_profile_json=brand_profile_json,
                    target_month=target_month,
                    posts_per_week=posts_per_week,
                    client_now_utc_iso=client_now,
                    timezone=timezone,
                    posting_hour_local=posting_hour_local,
                    post_index=i,
                    total_posts=n_posts,
                    # Pass the pre-computed slot so the model just writes content
                    assigned_slot=slot,
                )

                caption = (result.get("body_text") or "").strip() or None

                h = result.get("hashtags") or ""
                if isinstance(h, list):
                    hashtags = " ".join(str(x).strip() for x in h if str(x).strip()).strip() or None
                else:
                    hashtags = str(h).strip() or None

                structured = result.get("structured") or {}

                # Always use the Python-computed slot — never trust the model's
                scheduled_at_str: str = slot
                try:
                    scheduled_at = datetime.fromisoformat(
                        scheduled_at_str.replace("Z", "+00:00")
                    )
                except Exception:
                    scheduled_at = None

                draft = ContentDraft(
                    id=uuid.uuid4(),
                    topic_chat_id=topic_chat_id,
                    brand_id=brand_id,
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
                print(f"  [{plat_id}] Post {i+1} FAILED: {e}")
                db.add(ContentDraft(
                    id=uuid.uuid4(),
                    topic_chat_id=topic_chat_id,
                    brand_id=brand_id,
                    platform=plat_id,
                    status="FAILED",
                    last_error=str(e),
                    created_at=db_now,
                    updated_at=db_now,
                ))
                plat_failed += 1

        db.commit()   # commit per platform — partial success is better than none

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
        "created":    total_created,
        "generated":  total_generated,
        "failed":     total_failed,
        "platforms":  platform_summary,
        "weeks_remaining": round(
            _remaining_weeks_in_month(year, month, now_utc, tz), 2
        ),
    }