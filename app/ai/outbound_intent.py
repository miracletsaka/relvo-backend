"""
Intent detection for outbound calling in chat.
Cheap keyword gate first, then one small Muse call. Phone numbers are read with a regex, never by the model.
"""
import re

from app.ai.model_client import generate_json

TRIGGER_RE = re.compile(r"\b(call|phone|dial|ring|cold[- ]?call|outreach|outbound|prospect|reach out)\b", re.I)
PHONE_RE = re.compile(r"(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}")
INTENTS = {"call_number", "find_and_call", "none"}

SYSTEM = """You classify messages for a sales assistant that can make phone calls.
Return JSON: {"intent": "call_number" | "find_and_call" | "none", "business_type": "", "city": "", "count": 5, "notes": ""}
- call_number: the user wants to call one specific phone number.
- find_and_call: the user wants you to FIND businesses registered on the platform (optionally a type of business and/or a place) and call them to pitch or qualify.
- none: anything else (writing ads, scheduling posts, questions, advice).
business_type and city may be empty. count: how many businesses (default 5, max 10). notes: anything the user said about what to say on the call."""


def _count(value) -> int:
    try:
        return max(1, min(int(value), 10))
    except Exception:
        return 5


def detect_outbound_intent(message: str) -> dict:
    text = (message or "").strip()
    if not TRIGGER_RE.search(text):
        return {"intent": "none"}

    phones = [p.strip() for p in PHONE_RE.findall(text)]
    try:
        data = generate_json(text, SYSTEM, fast=True, temperature=0, max_output_tokens=700)
    except Exception as e:
        print("[OUTBOUND INTENT] model failed:", e)
        data = {}

    intent = data.get("intent") if data.get("intent") in INTENTS else None
    if intent is None:
        intent = "call_number" if phones else "none"   # model failed: trust the phone number
    if intent == "call_number" and not phones:
        intent = "none"

    return {
        "intent": intent,
        "business_type": str(data.get("business_type") or "").strip(),
        "city": str(data.get("city") or "").strip(),
        "count": _count(data.get("count") or 5),
        "notes": str(data.get("notes") or "").strip(),
        "phones": phones[:5],
    }
