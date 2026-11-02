"""
The agent: picks the best time to post, based on what it knows about the business.
On Windows run once:  pip install tzdata
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.ai.model_client import generate_json

SYSTEM = """You are a social media strategist for small businesses.
Pick the best time to publish ONE Facebook post for this business, within the next 7 days,
in the business's local time. Think about when its customers are online.
Return JSON: {"post_at_local": "YYYY-MM-DD HH:MM", "reason": "one short sentence"}
Rules: at least 1 hour after 'Now'. Use 24-hour time."""


def suggest_post_time(context: str, caption: str, tz_name: str = "Africa/Blantyre") -> dict:
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    user = f"Now (local): {now:%A %Y-%m-%d %H:%M}\nBusiness: {context}\nPost: {caption}"

    try:
        data = generate_json(user, SYSTEM, fast=True, temperature=0.4, max_output_tokens=1000)
        when = datetime.strptime(data["post_at_local"], "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        reason = str(data.get("reason") or "").strip()
    except Exception as e:
        print("[POST TIME] fallback:", e)
        when = (now + timedelta(days=1)).replace(hour=18, minute=30, second=0, microsecond=0)
        reason = "Evening slot, when most people browse after work."

    # Keep inside Facebook's window (10 minutes to 30 days)
    if when < now + timedelta(minutes=30):
        when = now + timedelta(hours=2)
    if when > now + timedelta(days=29):
        when = now + timedelta(days=29)

    return {
        "post_at_unix": int(when.timestamp()),
        "post_at_local": when.strftime("%Y-%m-%d %H:%M"),
        "reason": reason,
    }