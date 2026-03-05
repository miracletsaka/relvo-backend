# backend/app/services/ai_generator.py
import os
import json
import re
from typing import Dict, Any, Optional, List
import random
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _safe_list(x):
    if not x:
        return []
    if isinstance(x, list):
        return x
    return [x]


def _brand_context_block(
    brand_id: str,
    brand_profile_summary: Optional[str] = None,
    brand_profile_json: Optional[dict[str, Any]] = None,
) -> str:
    tone_tags = []
    services = []
    audiences = []
    positioning = []
    cta_style = None
    colors = []

    if isinstance(brand_profile_json, dict):
        tone_tags = _safe_list((brand_profile_json.get("tone") or {}).get("tags"))
        services = _safe_list(brand_profile_json.get("products_services"))
        audiences = _safe_list(brand_profile_json.get("audiences"))
        positioning = _safe_list((brand_profile_json.get("positioning") or {}).get("value_props"))
        cta_style = brand_profile_json.get("cta_style")
        colors = _safe_list(brand_profile_json.get("colors"))

    return f"""
BRAND CONTEXT:
Brand: {brand_id}
Summary: {brand_profile_summary or "(No summary provided)"}
Tone tags: {", ".join(map(str, tone_tags)) if tone_tags else "(not provided)"}
Audiences: {", ".join(map(str, audiences)) if audiences else "(not provided)"}
Products/Services: {", ".join(map(str, services)) if services else "(not provided)"}
Value props: {", ".join(map(str, positioning)) if positioning else "(not provided)"}
CTA style: {json.dumps(cta_style, ensure_ascii=False) if cta_style else "(not provided)"}
Colors: {", ".join(map(str, colors)) if colors else "(not provided)"}
""".strip()


class PostOutput(BaseModel):
    hook: str = Field(..., description="Opening hook line only, 10 words max, plain text no markdown")
    subheading: str = Field(..., description="Product intro line only, 14 words max, plain text no markdown")
    bullets: List[str] = Field(..., min_length=3, max_length=3, description="3 key benefits, plain text no markdown")
    proof: str = Field(..., description="Social proof line only, 9 words max, plain text no markdown")
    cta: str = Field(..., description="Call to action line only, 10 words max, plain text no markdown")
    full_caption: str = Field(..., description="Complete formatted ad copy with all sections, emojis, bullets, line breaks - 15-30 lines total, ready to post, PLAIN TEXT ONLY NO MARKDOWN")
    hashtags: List[str] = Field(default_factory=list, description="Array of hashtags like #Tag")
    scheduled_at: str = Field(..., description="ISO 8601 UTC ends with Z")
    image_prompt: Optional[str] = Field(default=None, description="Simple background prompt - 1-2 colors, minimal objects, 10-15 words max")
    video_concept: Optional[str] = Field(default=None)
    thumbnail_prompt: Optional[str] = Field(default=None)
    media_prompt: Optional[str] = Field(default=None)


def strip_markdown(text: str) -> str:
    """Remove common Markdown formatting characters"""
    if not text:
        return text
    
    # Remove bold **text** and __text__
    text = text.replace('**', '')
    text = text.replace('__', '')
    
    # Remove italic *text* and _text_ (but preserve * for bullet points at line start)
    # Only remove * that are used for emphasis (not at line start for bullets)
    text = re.sub(r'(?<!\n)(?<!\n\n)(?<!\n )(?<!^\*)\*(?!\s)', '', text, flags=re.MULTILINE)
    text = re.sub(r'(?<!^)_(?!$)', '', text, flags=re.MULTILINE)
    
    # Remove inline code `text`
    text = text.replace('`', '')
    
    # Remove headers ### text
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Remove strikethrough ~~text~~
    text = text.replace('~~', '')
    
    return text

AD_STYLES = [
    "hook_checklist",
    "story",
    "scenario",
    "problem_agitate",
    "case_study",
    "controversial",
    "question_led",
    "before_after",
]
def get_ad_style_instructions(style: str) -> str:
    styles = {

        "hook_checklist": """
STYLE: Hook + Checklist

Example structure:
🚀 Stop replying to customers manually.

Our AI WhatsApp assistant answers customers instantly and captures leads for you.

Imagine having an assistant that:
✅ Replies instantly 24/7
✅ Answers common questions automatically
✅ Captures leads while you sleep
✅ Books appointments
✅ Never misses a message

Perfect for:
💼 * Online stores
💼 * Service businesses
💼 * Busy founders

Start automating your customer conversations today.
""",

        "story": """
STYLE: Personal Story

Example:
A few months ago, a small business owner was drowning in WhatsApp messages. Customers waited hours for replies.

Then they installed an AI assistant.

Within weeks:
✅ Replies became instant
✅ Customers got answers 24/7
✅ Sales started increasing

Now the business runs smoother — even at night.

If you run a business that receives messages daily, this could help you too.
""",

        "scenario": """
STYLE: Scenario

Example:
It's 11pm. Your phone keeps buzzing. Customers asking the same questions again and again.

Now imagine every message getting an instant reply.

With an AI WhatsApp assistant:
✅ Customers get answers immediately
✅ Orders are captured automatically
✅ You stop replying manually

Hundreds of businesses already automate their chats.

Your business can too.
""",

        "problem_agitate": """
STYLE: Problem → Solution

Example:
You're losing customers because replies are too slow.

Every unanswered message is a missed sale.

What if every customer received an instant reply?

This AI assistant can:
✅ Reply instantly
✅ Answer FAQs automatically
✅ Capture leads
✅ Work 24/7

Stop missing opportunities.
""",

        "case_study": """
STYLE: Mini Case Study

Example:
How a small shop tripled conversions using AI chat.

Before:
• 3–4 hour reply times
• Dozens of missed messages

After installing the assistant:
📊 Reply time: seconds
📈 More leads captured
⭐ Happier customers

Key features:
✅ Instant replies
✅ Automated answers
✅ 24/7 availability
""",

        "controversial": """
STYLE: Bold Claim

Example:
Hiring more staff won't fix slow customer replies.

The real problem is manual messaging.

Smart businesses now use AI assistants that:
✅ Reply instantly
✅ Handle repetitive questions
✅ Capture leads automatically

Automation is becoming the new customer service standard.
""",

        "question_led": """
STYLE: Question Led

Example:
Do customers message your business every day?

Do you answer the same questions repeatedly?

Have you ever replied too late and lost a sale?

An AI assistant can:
✅ Reply instantly
✅ Answer FAQs
✅ Capture leads 24/7

Imagine never missing a customer message again.
""",

        "before_after": """
STYLE: Before vs After

Example:

BEFORE
❌ Messages pile up
❌ Customers wait hours
❌ Sales are missed

AFTER
✅ Instant replies
✅ Customers served 24/7
✅ More leads captured

All powered by an AI messaging assistant.
""",
    }

    return styles.get(style, styles["hook_checklist"])


def build_instructions(
    platform: str,
    brand_id: str,
    target_month: Optional[str] = None,
    posts_per_week: Optional[int] = None,
    client_now_utc_iso: Optional[str] = None,
    timezone: str = "Europe/London",
    posting_hour_local: int = 9,
    force_style: Optional[str] = None,
) -> str:

    # Pick style — forced for testing, random for production
    style = force_style or random.choice(AD_STYLES)
    style_instructions = get_ad_style_instructions(style)

    base = f"""
You are a professional copywriter creating commercial advertisements for {platform}. use "neuroflow AI" to differenciate from other neuroflow names.
Write in SIMPLE, CLEAR ENGLISH that anyone can understand — like explaining to a smart student.

🚨 CRITICAL FORMATTING RULES - READ FIRST:
❌ ABSOLUTELY NO Markdown syntax (no **, no *, no _, no #, no backticks, no ~~)
❌ NO asterisks for bold or italics emphasis
❌ NO special formatting characters for styling
✅ Use PLAIN TEXT ONLY with emojis and line breaks
✅ Use emojis for visual emphasis instead of bold
✅ Use UPPERCASE for emphasis if needed (use sparingly)
✅ Bullet points use * at the START of lines only (for actual bullet lists, not emphasis)

WRONG: "🚀 **Introducing** the Future!"
RIGHT: "🚀 Introducing the Future!"

WRONG: "This is *amazing* technology"
RIGHT: "This is amazing technology" or "This is AMAZING technology"

CRITICAL: Generate TWO outputs:
1. Individual fields (hook, subheading, bullets, proof, cta) - SHORT versions for structured data (all plain text)
2. full_caption field - COMPLETE formatted ad using the narrative style below (all plain text)

{style_instructions}

UNIVERSAL RULES (apply to ALL narrative styles):
- Write in a warm, direct, human voice — never robotic or corporate
- Use plain text only — no markdown bold (**), no headers with #
- Emojis are allowed and encouraged where specified
- Keep paragraphs short — maximum 3 sentences each
- The caption must feel like it was written by a human marketer, not a template
- End with a strong, specific CTA relevant to the product
- Total length: 250-400 words

FORMATTING RULES FOR full_caption:
- Use PLAIN TEXT only — absolutely NO Markdown formatting whatsoever
- NO ** for bold, NO * for italics, NO _ for underline, NO # for headers
- Use proper line breaks between sections for readability
- Include ALL emojis (🚀, ✅, 💼, 🔹, 📈, 📲, 🌍, etc.) for visual appeal
- Use bullet points with * at line start for lists (literal asterisks for bullets, NOT markdown)
- For emphasis, use emojis or UPPERCASE words (sparingly, not every sentence)
- Keep it readable and well-spaced with blank lines between sections
- Total length: 15-30 lines of text
- Make it ready to copy-paste directly into social media

LANGUAGE STYLE:
✅ Simple, clear English — easy to understand
✅ Short, clear sentences — avoid complexity
✅ Active voice: "You get X" not "X is provided"
✅ Specific numbers when possible: "Save 5 hours daily" not "Save time"
✅ Conversational but professional — like a friendly expert
✅ Enthusiastic and helpful tone — make people excited to act

AVOID:
❌ Markdown formatting of any kind (**, *, _, #, `, ~~)
❌ Complex jargon or technical terms
❌ Long, complicated sentences
❌ Passive voice
❌ Vague claims without specifics
❌ Corporate buzzwords
""".strip()

    now_line = (
        f'- client_now_utc = "{client_now_utc_iso}" (THIS IS THE CURRENT TIME; do not schedule before this). '
        f'Schedule must be at least +2 hours after client_now_utc.'
        if client_now_utc_iso
        else "- client_now_utc is unknown; schedule in the future"
    )

    if target_month and posts_per_week:
        scheduling = f"""
SCHEDULING RULES:
- timezone_local = "{timezone}"
{now_line}
- target_month = "{target_month}" (YYYY-MM)
- posts_per_week = {posts_per_week}
- Prefer weekdays (Mon-Fri) and spread evenly across the month.
- Default posting time is {posting_hour_local:02d}:00 local time; convert to UTC and output scheduled_at ending with Z.
""".strip()
    else:
        scheduling = f"""
SCHEDULING RULES:
- timezone_local = "{timezone}"
{now_line}
- Choose the next valid weekday at {posting_hour_local:02d}:00 local time.
- Convert to UTC and output scheduled_at ending with Z.
""".strip()

    image_prompt_rules = f"""
IMAGE PROMPT RULES (CRITICAL - READ CAREFULLY):

YOU MUST GENERATE EXTREMELY BACKGROUNDS:

MANDATORY REQUIREMENTS:
1. ONLY 1-2 solid colors (use brand colors if provided, otherwise: green, blue, yellow, orange, purple, red)
2. MAXIMUM 1 object OR zero objects (strongly prefer zero objects)
3. If including 1 object: must be geometric shape ONLY (circle, rounded square, leaf shape, abstract curve)
4. NO complex illustrations, NO multiple objects, NO 3D renders, NO detailed textures, NO patterns
5. Portrait orientation 4:5 (1080x1350)
6. 80%+ of canvas should be EMPTY solid color for text placement
7. Keep prompt under 15 words maximum

GOOD EXAMPLES (copy this exact style):
✅ "Professional marketing advertisement photo for AI WhatsApp chatbot.

Main subject:
Business owner holding smartphone showing WhatsApp chatbot conversation.

Scene:
Clean blue gradient background,
modern office lighting,
minimal environment.

Composition:
Phone centered,
person slightly to side,
clean empty space for text.

Style:
Ultra realistic photography,
agency advertisement,
soft shadows,
premium lighting.

Portrait 4:5 composition.
No text."

BAD EXAMPLES (NEVER generate like this):
❌ "Business team in a modern office analyzing AI data on tablets and screens, bright lighting, clean professional setting, portrait 4:5".
❌ "Colorful 3D shapes, multiple objects, complex composition..."
❌ "Vibrant abstract design with many elements and textures..."
❌ "Playful arrangement of geometric shapes scattered across..."
❌ "Dynamic colorful background with various elements..."
❌ Any prompt with words: multiple, various, collection, arrangement, scattered, dynamic, playful, complex, detailed, realistic texture, 3D, rendered

SIMPLICITY CHECKLIST — YOUR PROMPT MUST PASS ALL:
- Colors: 1 or 2 only? ✓
- Objects: 0 or 1 shape? ✓
- Empty space: 80%+ for text? ✓
- Portrait 4:5 ratio? ✓
- Under 15 words? ✓
- No complex descriptors? ✓

FINAL OUTPUT: One very short sentence (10-15 words maximum) describing the colored background.
Example format: "Solid [color] background, [optional: one shape location], flat design, portrait 4:5"
""".strip()

    return "\n\n".join([base, scheduling, image_prompt_rules]).strip()


def generate_post(
    topic_text: str,
    platform: str,
    brand_id: str,
    brand_profile_summary=None,
    brand_profile_json=None,
    target_month: str | None = None,
    posts_per_week: int | None = None,
    client_now_utc_iso: str | None = None,
    timezone: str = "Europe/London",
    posting_hour_local: int = 9,
) -> Dict[str, Any]:

    brand_ctx = _brand_context_block(brand_id, brand_profile_summary, brand_profile_json)

    instructions = build_instructions(
        platform=platform,
        brand_id=brand_id,
        target_month=target_month,
        posts_per_week=posts_per_week,
        client_now_utc_iso=client_now_utc_iso,
        timezone=timezone,
        posting_hour_local=posting_hour_local,
    )

    user_input = f"""

{brand_ctx}


TOPIC:

{topic_text}


PLATFORM:

{platform}


Generate:

1. A complete formatted advertisement in the 'full_caption' field following ALL 10 steps with emojis and proper formatting - USE PLAIN TEXT ONLY, NO MARKDOWN

2. Individual short fields (hook, subheading, bullets, proof, cta) for structured data - ALL PLAIN TEXT, NO MARKDOWN

3. A PROFESSIONAL marketing image_prompt describing a realistic advertisement scene based on the topic.



IMAGE PROMPT RULES:

- The image MUST visually represent the TOPIC
- Include the PRODUCT or SERVICE being advertised
- Include realistic people when appropriate
- Include UI screens when relevant (chatbot, dashboard, app)
- Should look like a professional agency advertisement
- Clean modern background
- Realistic lighting
- Portrait 4:5 composition
- Maximum 40 words



GOOD EXAMPLES:

Chatbot:
"Professional woman holding phone showing WhatsApp chatbot conversation, clean blue background, modern marketing style, portrait 4:5"

Furniture:
"Luxury sofa in modern living room, natural light, clean interior design, premium photography, portrait 4:5"

Voice AI:
"Business owner talking on smartphone, call interface visible, modern office background, marketing style, portrait 4:5"



CRITICAL REMINDERS:

- NO ** or * or _ or # formatting

- Full caption should be long with emojis and line breaks

- Image must clearly show the topic visually

- Avoid abstract backgrounds only

""".strip()

    resp = client.responses.parse(
        model=MODEL,
        instructions=instructions,
        input=user_input,
        text_format=PostOutput,
    )

    data: PostOutput = resp.output_parsed

    # Strip any Markdown formatting that might have slipped through
    full_caption_cleaned = strip_markdown(data.full_caption or "")
    hook_cleaned = strip_markdown(data.hook or "")
    subheading_cleaned = strip_markdown(data.subheading or "")
    proof_cleaned = strip_markdown(data.proof or "")
    cta_cleaned = strip_markdown(data.cta or "")

    # Normalize bullets / hashtags
    bullets = [strip_markdown(str(x).strip()) for x in (data.bullets or []) if str(x).strip()][:3]
    while len(bullets) < 3:
        bullets.append("")

    hashtags_list = [str(x).strip() for x in (data.hashtags or []) if str(x).strip()]
    hashtags = " ".join(hashtags_list).strip()

    structured = {
        "hook": hook_cleaned.strip(),
        "subheading": subheading_cleaned.strip(),
        "bullets": bullets,
        "proof": proof_cleaned.strip(),
        "cta": cta_cleaned.strip(),
        "hashtags": hashtags_list,
        "scheduled_at": data.scheduled_at,
        "image_prompt": data.image_prompt,
        "video_concept": data.video_concept,
        "thumbnail_prompt": data.thumbnail_prompt,
        "media_prompt": data.media_prompt,
    }

    return {
        "body_text": full_caption_cleaned.strip(),  # Use the complete cleaned caption
        "hashtags": hashtags,
        "scheduled_at": data.scheduled_at,
        "media_prompt": data.media_prompt,
        "structured": structured,
    }