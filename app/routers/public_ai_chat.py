import os
from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from app.ai.public_context import PUBLIC_PLATFORM_CONTEXT
import json
import base64
from io import BytesIO

router = APIRouter(prefix="/public-ai-chat", tags=["Public AI Chat"])

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class PublicImageRefineRequest(BaseModel):
    image_base64: str
    prompt: str | None = None

class PublicChatRequest(BaseModel):
    message: str
    history: list[dict] = []

class PublicCampaignRequest(BaseModel):
    prompt: str
    product_image_url: str | None = None


@router.post("/generate-campaign")
def public_generate_campaign(payload: PublicCampaignRequest):
    prompt = (payload.prompt or "").strip()

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.75,
        messages=[
            {
                "role": "system",
                "content": """
Return STRICT JSON only.

Create campaign data for a 1080x1350 marketing post.

Use these exact fields:
{
  "headline": "",
  "subheadline": "",
  "description": "",
  "product_name": "",
  "product_description": "",
  "campaign_label": "",
  "cta_text": "",
  "offer_value": "",
  "offer_label": "",
  "price_label": "",
  "feature_1": "",
  "feature_2": "",
  "feature_3": "",
  "image_prompt": ""
}

Rules:
- Extract product/service name if provided.
- Extract price if provided.
- Extract offer/discount if provided.
- If no offer exists, keep offer fields empty.
- Make headline short and punchy.
- Make description practical and specific.
- image_prompt should describe the exact product/service visual needed.
""",
            },
            {"role": "user", "content": prompt},
        ],
    )

    raw = res.choices[0].message.content or "{}"

    try:
        campaign_data = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=500, detail="AI returned invalid JSON")

    hero_image = payload.product_image_url or ""

    campaign_data["heroImage"] = hero_image
    campaign_data["imageSlots"] = {
        "hero_person": {"url": hero_image} if hero_image else {}
    }

    campaign_data["logo"] = ""
    campaign_data["companyName"] = "Your Business"
    campaign_data["location"] = "Online"

    return {
        "campaign_data": campaign_data,
        "canvas_width": 1080,
        "canvas_height": 1350,
        "background_image": None,
        "message": "Preview generated. Sign in to save, edit, or export this campaign.",
        "cta": {
            "label": "Sign in to save this campaign",
            "href": "/auth/login",
        },
    }


@router.post("/reply")
def public_chat_reply(payload: PublicChatRequest):
    user_text = (payload.message or "").strip()

    if not user_text:
        raise HTTPException(status_code=400, detail="Message is required")

    history = payload.history[-10:]

    messages = [
        {
    "role": "system",
    "content": PUBLIC_PLATFORM_CONTEXT,
}
    ]

    for item in history:
        role = item.get("role")
        text = (item.get("text") or item.get("content") or "").strip()

        if role in ["user", "assistant"] and text:
            messages.append({"role": role, "content": text})

    messages.append({"role": "user", "content": user_text})

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.75,
            messages=messages,
        )

        reply = (res.choices[0].message.content or "").strip()

        return {
            "reply": reply,
        }

    except Exception:
        return {
            "reply": "I can help you think through the business strategy. Tell me what you’re trying to improve — leads, content, sales, customer support, or operations.",
        }

@router.post("/refine-image")
def refine_public_image(payload: PublicImageRefineRequest):
    if not payload.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")

    image_base64 = payload.image_base64

    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]

    image_bytes = base64.b64decode(image_base64)

    prompt = payload.prompt or """
Refine this social media campaign poster into a premium, polished, high-conversion marketing image.

Keep the same message, product, offer, CTA, and layout intention.
Improve:
- typography hierarchy
- contrast
-premium fonts
- spacing
- image balance
- premium advertising feel
- background harmony
- readability

Do not add fake logos.
Do not add extra unrelated text.
Do not change the core offer or product message.
"""

    result = client.images.edit(
        model="gpt-image-1",
        image=("campaign.png", image_bytes, "image/png"),
        prompt=prompt,
        quality="medium",
        size="1024x1536",
    )

    b64 = result.data[0].b64_json

    return {
        "image_base64": f"data:image/png;base64,{b64}",
        "message": "Image refined successfully.",
    }