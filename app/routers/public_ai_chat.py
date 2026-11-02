from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.ai.model_client import generate_from_messages
from app.ai.public_context import PUBLIC_PLATFORM_CONTEXT
from app.services.ad_brief import build_brief
from app.services.muse_image import generate_background

router = APIRouter(prefix="/public-ai-chat", tags=["Public AI Chat"])


class ChatReq(BaseModel):
    message: str
    history: list[dict] = []


class CampaignReq(BaseModel):
    prompt: str
    product_image_url: str | None = None


@router.post("/generate-campaign")
def generate_campaign(p: CampaignReq):
    prompt = (p.prompt or "").strip()
    if not prompt:
        raise HTTPException(400, "Prompt is required")
    try:
        brief = build_brief(prompt)
    except Exception as e:
        print("[BRIEF] failed:", e)
        raise HTTPException(500, "Could not build the ad brief")

    bg = generate_background(brief["muse_prompt"])  # None = gradient fallback
    brief["heroImage"] = p.product_image_url or ""
    return {
        "campaign_data": brief,
        "brief": {
            "layout": brief["layout"],
            "mood": brief["mood"],
            "palette": brief["palette"],
        },
        "background_image": bg,
        "message": "Preview generated.",
    }


@router.post("/reply")
def reply(p: ChatReq):
    text = (p.message or "").strip()
    if not text:
        raise HTTPException(400, "Message is required")

    msgs = [{"role": "system", "content": PUBLIC_PLATFORM_CONTEXT}]
    for h in p.history[-10:]:
        t = (h.get("text") or "").strip()
        if h.get("role") in ("user", "assistant") and t:
            msgs.append({"role": h["role"], "content": t})
    msgs.append({"role": "user", "content": text})

    try:
        return {"reply": generate_from_messages(
            msgs, fast=True, temperature=0.75, max_output_tokens=1200)}
    except Exception as e:
        print("[REPLY] failed:", e)
        return {"reply": "Tell me what you want to improve: leads, content, sales, support or operations."}