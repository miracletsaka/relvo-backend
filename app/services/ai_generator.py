# backend/app/services/ai_generator.py
import os
import json
import re
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
    return text.strip()


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


def _tone_instruction(
    tone_name: Optional[str] = None,
    tone_label: Optional[str] = None,
    tone_description: Optional[str] = None,
    tone_prompt_instruction: Optional[str] = None,
) -> str:
    """
    Build tone context block.
    Priority:
      1. tone_prompt_instruction from DB (authoritative — set by admin)
      2. Built-in rules by tone_name slug (fallback)
      3. tone_description freetext (last resort)
    """
    name = (tone_name or "").strip().lower()

    builtin_rules = {
        "inform": "Write in a clear, helpful, factual style. Prioritize clarity over hype. Teach or explain something useful. CTA should feel soft and appropriate, not aggressive.",
        "advertise": "Write persuasively and commercially. Lead with benefit, urgency, or positioning. CTA should be strong and action-oriented. Focus on conversion.",
        "alert": "Write with urgency and importance. Shorter sentences. Get to the point quickly. Highlight the consequence or key action clearly.",
        "vacancy": "Write like a high-quality recruitment post. Make the role and opportunity clear. Keep it credible, direct, and professional. CTA should be about applying or learning more.",
        "announce": "Write like a professional announcement. Clear, confident, and official. Suitable for launches, updates, milestones, or news.",
        "educate": "Write to simplify something important. Make the content easy to understand. Focus on value and learning. CTA can invite the reader to learn more.",
        "inspire": "Write with energy and aspiration. Make the reader feel possibility, momentum, or ambition. Keep it authentic, not cheesy.",
        "testimonial": "Write with trust and proof. Lean into outcomes, real experience, or customer perspective. Make credibility the core of the message.",
        "promote": "Write to spotlight an offer, product, service, or opportunity. Highlight what makes it attractive. CTA should be clear and commercial.",
        "behind-the-scenes": "Write in a more human, natural, authentic voice. Show process, effort, people, or story behind the work.",
        "entertain": "Write in a playful, engaging, attention-grabbing way. Still keep it brand-safe and readable.",
        "question": "Write to spark conversation. Lead with a compelling question. Invite the audience to think and respond.",
    }

    # Use DB instruction if provided (highest priority)
    instruction = (tone_prompt_instruction or "").strip()

    # Fall back to built-in by slug
    if not instruction:
        instruction = builtin_rules.get(name, "")

    # Fall back to description
    if not instruction and tone_description:
        instruction = f"Follow this tone style: {tone_description}"

    if not instruction:
        instruction = "(No tone rule. Write naturally for the platform and topic.)"

    return f"""TONE CONTEXT:
Tone name: {tone_name or "(not set)"}
Tone label: {tone_label or "(not set)"}
Tone description: {tone_description or "(not set)"}

TONE INSTRUCTION:
{instruction}""".strip()


def _platform_context_block(platform: str) -> str:
    p = (platform or "").strip().lower()

    rules = {
        "linkedin": "Professional and polished. Useful for business, credibility, education, and authority. Avoid slang-heavy copy.",
        "facebook": "Readable, broad-audience friendly, engaging. Can be slightly more direct and practical. Good for local businesses, service offers, and community-oriented messaging.",
        "instagram": "Visual-first, punchy, clean, engaging. Shorter lines work well. Should feel strong in a graphic and still support a caption.",
        "twitter": "Concise and attention-grabbing. Front-load the strongest point. Keep phrasing tight.",
        "tiktok": "Fast, punchy, scroll-stopping. Simple language. Strong hook is critical.",
        "youtube": "Clear and compelling. Good for educational or authority-led messaging.",
    }

    return f"""PLATFORM CONTEXT:
Platform: {platform}
Guidance: {rules.get(p, "Write clearly for the platform and keep the format easy to consume.")}""".strip()


def _compute_schedule_slots(
    target_month: str,
    posts_per_week: int,
    client_now_utc_iso: Optional[str],
    tz_name: str,
    posting_hour_local: int,
    n_posts: int,
) -> List[str]:
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, Exception):
        tz = ZoneInfo("Europe/London")

    try:
        year, month = int(target_month[:4]), int(target_month[5:7])
    except Exception:
        now = datetime.now(tz)
        year, month = now.year, now.month

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
# NOTE: review_text, review_author, offer_title, offer_cta, business_* fields
# are still present so the AI can write FALLBACK values when no real org data
# exists. When org data IS available, these get overwritten by org_data_loader.
# ─────────────────────────────────────────────────────────────────────────────
class CampaignCopyOutput(BaseModel):
    # ── Core campaign copy ─────────────────────────────────────────────
    headline:       str
    subheadline:    str
    product_name:   str
    description:    str

    feature_1:      str
    feature_2:      str
    feature_3:      str

    cta_text:       str

    full_caption:   str
    hashtags:       List[str]
    scheduled_at:   str

    image_prompt:   Optional[str] = None
    video_concept:  Optional[str] = None

    # ── Optional campaign labels ──────────────────────────────────────
    campaign_label:  Optional[str] = ""
    collection_label: Optional[str] = ""
    footer_label:    Optional[str] = ""

    # ── Optional offer copy ───────────────────────────────────────────
    offer_value:    Optional[str] = ""
    offer_label:    Optional[str] = ""

    # ── Optional helper labels ────────────────────────────────────────
    proof:          Optional[str] = ""


CONTENT_ANGLES = [
    "benefit_led",
    "problem_solution",
    "trust_led",
    "educational",
    "offer_led",
    "authority_led",
    "story_led",
]

def _angle_example(angle: str) -> str:
    examples = {
        "benefit_led":       "ANGLE: Benefit Led\nLead with the biggest positive outcome. Make the result obvious fast. Then support with 2-3 concrete points and a CTA.",
        "problem_solution":  "ANGLE: Problem → Reality → Solution\nStart with a real-life situation, not a generic problem.Make it feel like something the reader experiences daily.",
        "trust_led":         "ANGLE: Trust Led\nLead with proof, confidence, professionalism, or credibility. Use this when reassurance matters.",
        "educational":       "ANGLE: Educational\nTeach or explain something useful. Structure the message so it feels valuable even before the CTA.",
        "offer_led":         "ANGLE: Offer Led\nLead with the offer, deal, opportunity, or headline incentive. Useful for promotional or conversion content.",
        "authority_led":     "ANGLE: Authority Led\nPosition the brand as capable, experienced, modern, or ahead of the curve. Useful for B2B, consulting, and expertise-driven messaging.",
        "story_led":         "ANGLE: Story Led\nUse a narrative or human angle. Good for testimonial, behind-the-scenes, or transformation style content.",
    }
    return examples.get(angle, examples["benefit_led"])


def _pick_angle_from_tone(tone_name: Optional[str]) -> str:
    name = (tone_name or "").strip().lower()
    if name in {"inform", "educate"}:     return "educational"
    if name in {"advertise", "promote"}:  return "offer_led"
    if name == "alert":                   return "problem_solution"
    if name == "testimonial":             return "trust_led"
    if name in {"behind-the-scenes", "inspire"}: return "story_led"
    if name in {"announce", "vacancy"}:   return "authority_led"
    return random.choice(CONTENT_ANGLES)


def build_system_prompt(
    platform: str,
    brand_id: str,
    schedule_slots: List[str],
    angle: str,
    tone_name: Optional[str] = None,
    tone_label: Optional[str] = None,
    tone_description: Optional[str] = None,
    tone_prompt_instruction: Optional[str] = None,
    org_context_block: Optional[str] = None,
) -> str:
    angle_block    = _angle_example(angle)
    slots_block    = "\n".join(f"  Slot {i+1}: {s}" for i, s in enumerate(schedule_slots))
    tone_block     = _tone_instruction(tone_name, tone_label, tone_description, tone_prompt_instruction)
    platform_block = _platform_context_block(platform)

    # Inject real org data context if available
    org_block = ""
    if org_context_block:
        org_block = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REAL ORG DATA (do not hallucinate — use this)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{org_context_block}

IMPORTANT: The review_text, review_author, offer_title, offer_cta, business_tagline,
business_description, business_type, and business_website fields will be OVERWRITTEN
with real database values after generation. Focus your energy on writing excellent
hook, subheading, bullets, proof, cta, and full_caption copy.
""".strip()

    return f"""You are a senior social-media copywriter creating a high-performing social post for {platform}.
Always refer to the product or company accurately based on the provided brand context.
Do not invent facts that are not supported by the topic or brand context.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATTING — NON-NEGOTIABLE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ PLAIN TEXT ONLY — no Markdown of any kind
✅ Emojis allowed when appropriate
✅ UPPERCASE allowed for emphasis, but use sparingly
✅ Bullet lines in captions may start with * if useful
✅ Keep text clean and copy-paste ready
✅ Use simple student english, avoid jargon or complex phrasing

❌ Do not use the word "Transform" or "Elevate" in the copy — these are overused and generic marketing buzzwords

❌ NO ** bold, NO * italic, NO _ underline, NO # headers, NO ` code, NO ~~ strike

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PLATFORM + TONE + ANGLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{platform_block}

{tone_block}

{angle_block}

{org_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADVANCED CAPTION RULES (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
* Do NOT start every caption with a question
* Vary opening styles:
  - statement
  - insight
  - bold claim
  - relatable situation
  - short story
  - direct observation
* Avoid generic phrases:
  - "scale faster"
  - "unlock potential"
  - "increase efficiency"
  - "seamless solutions"
* Write like a real human speaking to a specific person
* Make it feel like a real situation, not marketing copy
* If it sounds like a template, rewrite it
* Always speak to a specific audience from BRAND CONTEXT
* Make the reader feel "this is for me"
* full_caption must NOT repeat hook/subheading word-for-word
* It should expand the idea in a natural flow
* It should feel like a conversation, not a list

FIXED STYLE ON FULL_CAPTION FIELD:
Most businesses dont realise how much time they lose on small, repetitive work.

Chasing follow-ups.
Updating systems.
Replying late to customers.

It doesnt feel like a big problem — until it starts slowing everything down.

Thats where automation changes things.

Instead of doing more, you remove the work that shouldn’t be manual in the first place.

NeuroFlow AI helps you build that system.

Less chasing. More control. Better flow.

If you're serious about growing without burning time, it's worth a closer look.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRUCTURED FIELD RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
hook:        short, strong, visually usable — 4-10 words
subheading:  one supporting line — 6-16 words
bullets:     exactly 3, each short and clean, no duplicate meaning
proof:       short trust / proof / credibility line
cta:         short and direct, matched to tone

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCHEDULE SLOTS — PICK EXACTLY ONE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{slots_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMAGE PROMPT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write a realistic marketing image prompt (30-40 words):
* Must visually represent the topic and tone
* Prefer real people / product / environment / device where appropriate
* Clean modern composition, portrait 4:5, no text in image
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
    timezone: str = "Europe/London",
    posting_hour_local: int = 9,
    post_index: int = 0,
    total_posts: int = 1,
    assigned_slot: Optional[str] = None,
    tone_name: Optional[str] = None,
    tone_label: Optional[str] = None,
    tone_description: Optional[str] = None,
    tone_prompt_instruction: Optional[str] = None,   # ← NEW: from DB tones table
    org_context_block: Optional[str] = None,          # ← NEW: from org_data_loader
    org_structured_patch: Optional[Dict[str, Any]] = None,  # ← NEW: real data to merge
) -> Dict[str, Any]:

    brand_ctx = _brand_context_block(brand_id, brand_profile_summary, brand_profile_json)
    tone_ctx  = _tone_instruction(tone_name, tone_label, tone_description, tone_prompt_instruction)
    angle     = _pick_angle_from_tone(tone_name)

    if assigned_slot:
        slots = [assigned_slot]
        post_index = 0
    else:
        slots = _compute_schedule_slots(
            target_month=target_month or "",
            posts_per_week=posts_per_week or 3,
            client_now_utc_iso=client_now_utc_iso,
            tz_name=timezone,
            posting_hour_local=posting_hour_local,
            n_posts=total_posts,
        )

    system_prompt = build_system_prompt(
        platform=platform,
        brand_id=brand_id,
        schedule_slots=slots,
        angle=angle,
        tone_name=tone_name,
        tone_label=tone_label,
        tone_description=tone_description,
        tone_prompt_instruction=tone_prompt_instruction,
        org_context_block=org_context_block,
    )

    user_message = f"""{brand_ctx}

{tone_ctx}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOPIC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{topic_text}

PLATFORM: {platform}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write one strong social post that matches:
* the brand context
* the selected tone
* the platform
* the required structured output

Requirements:
1. Write full_caption in plain text with natural line breaks.
2. Fill hook, subheading, bullets, proof, cta in plain text.
3. Pick scheduled_at from the provided SCHEDULE SLOTS list — use Slot {post_index + 1}.
4. Write a realistic image_prompt suited to the topic and tone.
5. Keep the structured fields visually strong for graphic use.

CRITICAL:
* No markdown formatting anywhere
* No fake specifics
* No invented claims unless they are clearly framed generically
* Make the writing feel intentional, not generic
""".strip()

    print(f"[ai_generator] Generating post {post_index+1}/{total_posts} | platform={platform} | angle={angle} | tone={tone_name}")

    resp = client.beta.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        response_format=CampaignCopyOutput,
        temperature=0.8,
    )

    data: CampaignCopyOutput = resp.choices[0].message.parsed
    if data is None:
        raise ValueError(f"Model refused to generate: {resp.choices[0].message.refusal}")

    full_caption = strip_markdown(data.full_caption or "")

    hashtags_list = [str(h).strip() for h in (data.hashtags or []) if str(h).strip()]
    hashtags      = " ".join(hashtags_list).strip()
    final_slot    = assigned_slot or slots[min(post_index, len(slots) - 1)]

    # ── Build structured output from AI ──────────────────────────────────────
    structured = {
    # ── Core campaign copy ─────────────────────────────────────
    "headline":       strip_markdown(data.headline or ""),
    "subheadline":    strip_markdown(data.subheadline or ""),
    "product_name":   strip_markdown(data.product_name or ""),
    "description":    strip_markdown(data.description or ""),

    "feature_1":      strip_markdown(data.feature_1 or ""),
    "feature_2":      strip_markdown(data.feature_2 or ""),
    "feature_3":      strip_markdown(data.feature_3 or ""),

    "cta_text":       strip_markdown(data.cta_text or ""),

    "campaign_label": strip_markdown(data.campaign_label or ""),
    "collection_label": strip_markdown(data.collection_label or ""),
    "footer_label":   strip_markdown(data.footer_label or ""),

    "offer_value":    strip_markdown(data.offer_value or ""),
    "offer_label":    strip_markdown(data.offer_label or ""),

    "proof":          strip_markdown(data.proof or ""),

    # ── Metadata ───────────────────────────────────────────────
    "hashtags":       hashtags_list,
    "scheduled_at":   final_slot,
    "image_prompt":   data.image_prompt or "",
    "video_concept":  data.video_concept or "",

    "tone_name":      tone_name or "",
    "tone_label":     tone_label or "",
}

    # ── Merge real org data (overwrites AI fallbacks) ─────────────────────────
    # This is the key step: real DB data always wins over AI-generated values.
    if org_structured_patch:
        structured.update(org_structured_patch)
        print(f"[ai_generator] Merged real org data: {list(org_structured_patch.keys())}")

    print(f"[ai_generator] Generated OK | scheduled_at={final_slot} | caption_len={len(full_caption)}")

    return {
        "body_text":    full_caption,
        "hashtags":     hashtags,
        "scheduled_at": final_slot,
        "structured":   structured,
    }