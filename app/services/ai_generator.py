# backend/app/services/ai_generator.py
import os
import json
import re
import math
import random
import calendar
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from openai import OpenAI
from pydantic import BaseModel, Field

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_list(x):
    if not x:
        return []
    if isinstance(x, list):
        return x
    return [x]


def strip_markdown(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__',     r'\1', text)
    text = re.sub(r'\*(.*?)\*',     r'\1', text)
    text = re.sub(r'_(.*?)_',       r'\1', text)
    text = re.sub(r'^#{1,6}\s+',    '',    text, flags=re.MULTILINE)
    text = re.sub(r'~~(.*?)~~',     r'\1', text)
    text = text.replace('`', '')
    return text


def _brand_context_block(
    brand_id: str,
    brand_profile_summary: Optional[str] = None,
    brand_profile_json: Optional[Dict[str, Any]] = None,
) -> str:
    tone_tags   = []
    services    = []
    audiences   = []
    positioning = []
    cta_style   = None
    colors      = []

    if isinstance(brand_profile_json, dict):
        tone_tags   = _safe_list((brand_profile_json.get("tone") or {}).get("tags"))
        services    = _safe_list(brand_profile_json.get("products_services"))
        audiences   = _safe_list(brand_profile_json.get("audiences"))
        positioning = _safe_list((brand_profile_json.get("positioning") or {}).get("value_props"))
        cta_style   = brand_profile_json.get("cta_style")
        colors      = _safe_list(brand_profile_json.get("colors"))

    return f"""BRAND CONTEXT:
Brand: {brand_id}
Summary: {brand_profile_summary or "(No summary provided)"}
Tone tags: {", ".join(map(str, tone_tags)) if tone_tags else "(not provided)"}
Audiences: {", ".join(map(str, audiences)) if audiences else "(not provided)"}
Products/Services: {", ".join(map(str, services)) if services else "(not provided)"}
Value props: {", ".join(map(str, positioning)) if positioning else "(not provided)"}
CTA style: {json.dumps(cta_style, ensure_ascii=False) if cta_style else "(not provided)"}
Colors: {", ".join(map(str, colors)) if colors else "(not provided)"}""".strip()


def _compute_schedule_slots(
    target_month: str,
    posts_per_week: int,
    client_now_utc_iso: Optional[str],
    tz_name: str,                        # renamed from 'timezone' to avoid shadowing builtin
    posting_hour_local: int,
    n_posts: int,
) -> List[str]:
    """
    Fallback slot computation used only when assigned_slot is not provided
    (i.e. standalone usage outside the monthly generator).
    """
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, Exception):
        tz = ZoneInfo("Europe/London")

    try:
        year, month = int(target_month[:4]), int(target_month[5:7])
    except Exception:
        now = datetime.now(tz)
        year, month = now.year, now.month

    # ── Fix: never use the string param as datetime.timezone ─────────────────
    if client_now_utc_iso:
        try:
            now_utc = datetime.fromisoformat(client_now_utc_iso.replace("Z", "+00:00"))
            if now_utc.tzinfo is None:
                now_utc = now_utc.replace(tzinfo=ZoneInfo("UTC"))
        except Exception:
            now_utc = datetime.now(ZoneInfo("UTC"))
    else:
        now_utc = datetime.now(ZoneInfo("UTC"))

    days_in_month = calendar.monthrange(year, month)[1]
    all_slots: List[datetime] = []

    for day in range(1, days_in_month + 1):
        local_dt = datetime(year, month, day, posting_hour_local, 0, 0, tzinfo=tz)
        utc_dt   = local_dt.astimezone(ZoneInfo("UTC"))
        if local_dt.weekday() > 4:
            continue
        if utc_dt <= now_utc + timedelta(hours=2):
            continue
        all_slots.append(utc_dt)

    if not all_slots:
        cursor = now_utc + timedelta(hours=3)
        while len(all_slots) < n_posts:
            local_c = cursor.astimezone(tz)
            if local_c.weekday() <= 4:
                slot = datetime(
                    local_c.year, local_c.month, local_c.day,
                    posting_hour_local, 0, 0, tzinfo=tz
                )
                all_slots.append(slot.astimezone(ZoneInfo("UTC")))
            cursor += timedelta(days=1)

    if len(all_slots) <= n_posts:
        chosen = all_slots[:n_posts]
        while len(chosen) < n_posts:
            chosen.append(chosen[-1] + timedelta(days=7))
    else:
        step   = len(all_slots) / n_posts
        chosen = [all_slots[int(i * step)] for i in range(n_posts)]

    return [dt.strftime("%Y-%m-%dT%H:%M:%SZ") for dt in chosen]


# ── Structured output schema ──────────────────────────────────────────────────

class PostOutput(BaseModel):
    hook:          str            = Field(..., description="Opening hook — 10 words max, plain text, no markdown")
    subheading:    str            = Field(..., description="Product intro line — 14 words max, plain text")
    bullets:       List[str]      = Field(..., min_length=3, max_length=3, description="Exactly 3 key benefits, plain text")
    proof:         str            = Field(..., description="Social proof line — 9 words max, plain text")
    cta:           str            = Field(..., description="Call to action — 10 words max, plain text")
    full_caption:  str            = Field(..., description="Complete ad copy, 250-400 words, plain text with emojis and line breaks — NO markdown")
    hashtags:      List[str]      = Field(default_factory=list, description="Array of hashtags like #Tag")
    scheduled_at:  str            = Field(..., description="One ISO 8601 UTC timestamp from the provided SCHEDULE SLOTS list — copy exactly, ends with Z")
    image_prompt:  Optional[str]  = Field(default=None, description="Realistic marketing photo prompt, 30-40 words, portrait 4:5")
    video_concept: Optional[str]  = Field(default=None)


# ── Ad style library ──────────────────────────────────────────────────────────

AD_STYLES = [
    "story", "scenario", "problem_agitate",
    "case_study", "controversial", "question_led", "before_after",
]

def _get_style_example(style: str) -> str:
    examples = {
        "story": """STYLE: Personal Story
Write as if a real customer is telling their transformation story.
Open with a relatable struggle, show the turning point, end with the outcome.
Use "I" or "they" voice. 3-4 short paragraphs + bullet results + CTA.""",

        "scenario": """STYLE: Vivid Scenario
Paint a specific moment the reader recognises (a time, a place, a frustration).
Make them nod and say "that's me". Then present the solution as relief.
Short punchy paragraphs, present tense, end with CTA.""",

        "problem_agitate": """STYLE: Problem → Agitate → Solve
Name the pain → twist the knife (make it feel worse) → reveal the solution.
Use short sentences, escalating urgency, then flip to relief + CTA.""",

        "case_study": """STYLE: Mini Case Study
Before numbers → After numbers → Key features → CTA.
Use real-feeling metrics (even approximate). Keep it tight: 4 sections.""",

        "controversial": """STYLE: Contrarian Take
Open with a bold claim that challenges conventional wisdom.
Back it up with 2-3 punchy reasons. End with the smarter alternative + CTA.""",

        "question_led": """STYLE: Question Led
Open with 3 short questions the reader answers "yes" to.
Build tension, then reveal the solution. Close with a direct CTA.""",

        "before_after": """STYLE: Before / After
Show two clear states with emoji dividers (❌ Before / ✅ After).
Keep each side to 3-4 bullet points. Add 1 bridging line + CTA.""",
    }
    return examples.get(style, examples["problem_agitate"])


def build_system_prompt(
    platform: str,
    brand_id: str,
    schedule_slots: List[str],
    style: str,
) -> str:
    style_block = _get_style_example(style)
    slots_block = "\n".join(f"  Slot {i+1}: {s}" for i, s in enumerate(schedule_slots))

    return f"""You are a senior social-media copywriter creating a single paid advertisement for {platform}.
Always refer to the product as "NeuroFlow AI" to distinguish from other Neuroflow brands.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATTING — NON-NEGOTIABLE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ PLAIN TEXT ONLY — no Markdown of any kind
✅ Emojis encouraged for visual emphasis
✅ UPPERCASE for emphasis (use sparingly)
✅ Bullet lines start with * (literal asterisk for lists only)
✅ Blank lines between sections for readability

❌ NO ** bold, NO * italic, NO _ underline, NO # headers, NO ` code, NO ~~ strike

WRONG: "🚀 **Introducing** the Future!"
RIGHT: "🚀 Introducing the Future!"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AD STYLE TO FOLLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{style_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WRITING RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
* Simple clear English — explain like to a smart student
* Short sentences, active voice
* Specific numbers when possible ("Save 5 hours daily" not "Save time")
* Conversational but professional
* full_caption: 250-400 words, 15-30 lines, ready to copy-paste

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCHEDULE SLOTS — PICK EXACTLY ONE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
These are the only valid timestamps. Copy one exactly into scheduled_at:
{slots_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMAGE PROMPT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write a realistic marketing photo description (30-40 words):
* Must visually represent the topic
* Include the product/service being advertised
* Realistic people when appropriate; UI screens when relevant
* Clean modern background, portrait 4:5, no text in image

GOOD: "Professional woman holding phone showing WhatsApp chatbot conversation, clean blue background, modern marketing style, portrait 4:5"
BAD: "Colorful abstract shapes and dynamic elements with vibrant textures"
""".strip()


# ── Main generation function ──────────────────────────────────────────────────

def generate_post(
    topic_text: str,
    platform: str,
    brand_id: str,
    brand_profile_summary: Optional[str] = None,
    brand_profile_json: Optional[Dict[str, Any]] = None,
    target_month: Optional[str] = None,
    posts_per_week: Optional[int] = None,
    client_now_utc_iso: Optional[str] = None,
    timezone: str = "Europe/London",     # kept for API compatibility
    posting_hour_local: int = 9,
    post_index: int = 0,
    total_posts: int = 1,
    assigned_slot: Optional[str] = None,
) -> Dict[str, Any]:

    brand_ctx = _brand_context_block(brand_id, brand_profile_summary, brand_profile_json)
    style     = random.choice(AD_STYLES)

    # If the monthly scheduler pre-computed a slot, give the model exactly
    # one option so it has no choice but to use it.
    # Otherwise compute slots here (standalone / legacy usage).
    if assigned_slot:
        slots      = [assigned_slot]
        post_index = 0
    else:
        slots = _compute_schedule_slots(
            target_month=target_month or "",
            posts_per_week=posts_per_week or 3,
            client_now_utc_iso=client_now_utc_iso,
            tz_name=timezone,            # pass as tz_name to avoid builtin shadow
            posting_hour_local=posting_hour_local,
            n_posts=total_posts,
        )

    system_prompt = build_system_prompt(
        platform=platform,
        brand_id=brand_id,
        schedule_slots=slots,
        style=style,
    )

    user_message = f"""{brand_ctx}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOPIC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{topic_text}

PLATFORM: {platform}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Write the full_caption following the AD STYLE above — plain text, emojis, line breaks.
2. Fill the short structured fields (hook, subheading, bullets, proof, cta) — all plain text.
3. Pick scheduled_at from the SCHEDULE SLOTS list — use Slot {post_index + 1}.
4. Write a realistic image_prompt (30-40 words, portrait 4:5, no text in image).

CRITICAL: NO markdown formatting anywhere. PLAIN TEXT ONLY.""".strip()

    print(f"[ai_generator] Generating post {post_index+1}/{total_posts} | platform={platform} | style={style}")
    print(f"[ai_generator] System prompt length: {len(system_prompt)} chars")

    resp = client.beta.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        response_format=PostOutput,
        temperature=0.8,
    )

    data: PostOutput = resp.choices[0].message.parsed

    if data is None:
        refusal = resp.choices[0].message.refusal
        raise ValueError(f"Model refused to generate: {refusal}")

    print(f"[ai_generator] Generated OK | scheduled_at={data.scheduled_at} | caption_len={len(data.full_caption or '')}")

    full_caption = strip_markdown(data.full_caption or "").strip()
    hook         = strip_markdown(data.hook or "").strip()
    subheading   = strip_markdown(data.subheading or "").strip()
    proof        = strip_markdown(data.proof or "").strip()
    cta          = strip_markdown(data.cta or "").strip()
    bullets      = [strip_markdown(str(b).strip()) for b in (data.bullets or []) if str(b).strip()][:3]
    while len(bullets) < 3:
        bullets.append("")

    hashtags_list = [str(h).strip() for h in (data.hashtags or []) if str(h).strip()]
    hashtags      = " ".join(hashtags_list).strip()

    # Python always owns the final scheduled_at — never trust the model
    final_slot = assigned_slot or slots[min(post_index, len(slots) - 1)]

    structured = {
        "hook":          hook,
        "subheading":    subheading,
        "bullets":       bullets,
        "proof":         proof,
        "cta":           cta,
        "hashtags":      hashtags_list,
        "scheduled_at":  final_slot,
        "image_prompt":  data.image_prompt,
        "video_concept": data.video_concept,
    }

    return {
        "body_text":    full_caption,
        "hashtags":     hashtags,
        "scheduled_at": final_slot,
        "structured":   structured,
    }