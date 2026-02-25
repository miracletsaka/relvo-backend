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
NARRATIVE STYLE: HOOK + CHECKLIST (Classic Direct Response)

Write the full_caption using this structure:
1. OPENING HOOK (Emoji + bold statement that stops the scroll)
2. PRODUCT INTRODUCTION (one clear sentence — what it is and who it's for)
3. "Imagine having a smart assistant that:" (lead into checklist)
4. BENEFIT CHECKLIST (✅ format, 5-6 items — plain text only)
5. DIFFERENTIATION paragraph (what makes this different)
6. TARGET AUDIENCES (💼 with * bullets)
7. WHY CHOOSE US (🔹 format, 5 items)
8. URGENCY STATEMENT (one punchy line)
9. VALUE PROPOSITIONS (3 emoji lines)
10. CLOSING CTA
""",

        "story": """
NARRATIVE STYLE: PERSONAL STORY (Emotional Journey)

Write the full_caption as a personal story that leads into the product:

1. STORY OPENING — Start with "I remember when..." or "A few months ago..." or "Last year, [type of business] was struggling with..."
   Make it relatable, emotional, specific. 2-3 sentences.

2. THE STRUGGLE — Describe the pain vividly. What was being lost? Time? Money? Customers?
   Example: "Every night, messages piled up. Customers asking questions at 2am. No one to reply. Orders lost. Trust broken."

3. THE TURNING POINT — Introduce the product as the discovery that changed everything.
   Example: "Then we discovered something that changed everything."

4. THE TRANSFORMATION — Show specific results after using it. Use numbers or feelings.
   Example: "Within 2 weeks: response time dropped from 8 hours to 3 seconds. Sales went up. Stress went down."

5. BENEFIT CHECKLIST (✅ format, 4-5 items — frame as what they now enjoy)

6. INVITATION — Invite the reader into the same transformation.

7. TARGET AUDIENCES (💼 with * bullets)

8. CLOSING CTA with urgency
""",

        "scenario": """
NARRATIVE STYLE: VIVID SCENARIO (Scene Painting)

Write the full_caption by painting a vivid scenario the reader recognizes:

1. SCENE SETTER — Drop them into a specific moment. Use "It's 11pm..." or "Picture this:" or "You just got back from work..."
   Make it hyper-specific and visual. The reader should say "that's me."
   Example: "It's Friday evening. You're exhausted. But your phone won't stop buzzing — customer after customer asking the same questions. And you're the only one who can answer."

2. THE FRUSTRATION — Amplify the emotion. Don't rush to the solution.
   Example: "You wanted to rest. Instead you're typing replies manually. Again. For the 47th time today."

3. WHAT IF — Pivot with a "What if it didn't have to be this way?" moment.

4. INTRODUCE THE SOLUTION — Bring in the product as the exact answer to that scenario.

5. HOW IT WORKS (simple, plain language — 3-4 sentences max)

6. BENEFIT CHECKLIST (✅ format, 5 items)

7. WHO THIS IS FOR (💼 with * bullets)

8. PROOF LINE — "Hundreds of businesses are already doing this."

9. CLOSING CTA
""",

        "problem_agitate": """
NARRATIVE STYLE: PROBLEM → AGITATE → SOLVE (PAS Framework)

Write the full_caption using the PAS copywriting framework:

1. PROBLEM — State the core problem clearly and directly. One punchy sentence.
   Example: "You're losing customers every single day — and you don't even know it."

2. AGITATE — Make the problem feel urgent and painful. Use rhetorical questions.
   Example:
   "How many messages went unanswered last night?
   How many potential buyers moved on to your competitor?
   How many times did a customer ask a simple question — and nobody replied for hours?
   Every delayed reply is a lost sale. Every missed message is broken trust."

3. AMPLIFY THE COST — Make them feel the real cost of inaction.
   Example: "Over a month, that's hundreds of missed opportunities. Over a year? It could be the difference between a thriving business and a struggling one."

4. INTRODUCE THE SOLUTION — Present the product as the precise fix.

5. HOW IT SOLVES IT (✅ checklist, 5-6 items)

6. DIFFERENTIATION — Why this over other solutions?

7. TARGET AUDIENCES (💼 with * bullets)

8. URGENCY + CLOSING CTA
""",

        "case_study": """
NARRATIVE STYLE: MINI CASE STUDY (Result-First)

Write the full_caption as a mini case study leading with the outcome:

1. RESULT HEADLINE — Lead with the outcome first. Bold and specific.
   Example: "How a small online shop went from 2-hour reply times to instant responses — and tripled their sales in 30 days."

2. BACKGROUND — Briefly describe who the business was and their situation before.
   (Can be realistic and hypothetical: "A local clothing boutique...")

3. THE PROBLEM THEY HAD — Specific challenges. Numbers help.
   Example: "They were getting 200+ messages a day. One person managing everything. Average reply time: 4 hours. Customers were leaving."

4. WHAT THEY DID — Introduce the product as the solution they chose.

5. THE RESULTS — Specific, tangible outcomes with numbers.
   Example:
   "📊 Reply time: 4 hours → 3 seconds
   📈 Sales conversion: up 40%
   😌 Team stress: dramatically reduced
   ⭐ Customer satisfaction: all-time high"

6. WHAT MADE IT WORK (✅ checklist — key features that drove results)

7. "YOUR BUSINESS CAN DO THIS TOO" — Transition to the offer.

8. TARGET AUDIENCES (💼 with * bullets)

9. CLOSING CTA
""",

        "controversial": """
NARRATIVE STYLE: BOLD CLAIM / MYTH BUSTER (Pattern Interrupt)

Write the full_caption starting with a bold claim that stops the scroll:

1. CONTROVERSIAL OPENER — Challenge a common belief. Make it slightly provocative.
   Examples:
   "Hiring more staff is NOT the answer to slow customer service."
   "Your WhatsApp inbox is silently killing your business."
   "The biggest lie in business: 'We'll get back to you shortly.'"

2. EXPLAIN THE CLAIM — Back it up with logic and reality. 2-3 sentences.

3. THE REAL PROBLEM — Reframe what they think the issue is vs what it actually is.
   Example: "You don't have a staffing problem. You have an automation problem."

4. THE SOLUTION — Introduce the product as the smarter path.

5. HOW IT WORKS (plain language, conversational, 3-4 sentences)

6. BENEFIT CHECKLIST (✅ format, 5 items)

7. PROOF LINE — One line of social validation or a result.

8. TARGET AUDIENCES (💼 with * bullets)

9. CLOSING CTA — Tie back to the opening bold claim.
""",

        "question_led": """
NARRATIVE STYLE: QUESTION-LED (Socratic Pull)

Write the full_caption by opening with questions the reader answers "yes" to in their head:

1. QUESTION SERIES — 4-5 direct questions hitting their pain points. Each one should make them nod.
   Example:
   "Are you still replying to customer messages manually?
   Do you find yourself answering the same questions over and over?
   Have you ever lost a customer simply because you replied too late?
   Is your business available 24/7 — or only when YOU are awake?"

2. ACKNOWLEDGEMENT — Validate their experience.
   Example: "If you answered yes to any of these — you're not alone. And there IS a better way."

3. INTRODUCE THE SOLUTION

4. WHAT IT DOES (✅ checklist, 5-6 items)

5. DIFFERENTIATION paragraph

6. POSSIBILITY QUESTIONS (future-focused):
   Example:
   "What if your business replied instantly at 3am?
   What if every customer felt heard — automatically?
   What if you could focus on growth while your assistant handled support?"

7. TARGET AUDIENCES (💼 with * bullets)

8. CLOSING CTA
""",

        "before_after": """
NARRATIVE STYLE: BEFORE vs AFTER TRANSFORMATION (Visual Contrast)

Write the full_caption as a dramatic before/after transformation:

1. BEFORE PICTURE — Paint the painful "before" state vividly. Present tense. Raw and real.
   Example:
   "BEFORE:
   📵 Messages pile up overnight
   😤 Same questions answered 30 times a day
   ⏰ Customers waiting hours for simple replies
   💸 Sales slipping through unanswered chats
   🥵 You, burnt out and still falling behind"

2. THE SHIFT LINE — One powerful sentence between before and after.
   Example: "Then everything changed." or "Until [product] entered the picture."

3. AFTER PICTURE — The transformed reality. Same format, opposite energy.
   Example:
   "AFTER:
   ✅ Every message answered in seconds — automatically
   ✅ Customers served 24/7 without lifting a finger
   ✅ Your time freed for what actually grows the business
   ✅ More sales. Less stress. Zero missed chats.
   ✅ A business that works even while you sleep"

4. HOW — Brief explanation of what makes it possible (3-4 sentences)

5. WHO IT IS FOR (💼 with * bullets)

6. PROOF LINE — One result or social validation sentence.

7. URGENCY STATEMENT

8. CLOSING CTA
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