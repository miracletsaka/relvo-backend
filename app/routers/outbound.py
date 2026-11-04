"""
Outbound calling from chat. Targets are businesses REGISTERED in this app.

    POST /outbound/intent   does this chat message ask for a call?
    POST /outbound/search   find registered businesses that have a phone number
    POST /outbound/call     start the calls with your Retell agent
    GET  /outbound/calls    recent calls

Register in main.py:
    from app.routers import outbound
    app.include_router(outbound.router)
"""
from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai.outbound_intent import detect_outbound_intent
from app.database import get_db
from app.dependencies.org import get_current_org
from app.models.organisation import Organisation
from app.routers.outbound_settings import _row, to_e164_us
from app.services import retell_outbound
from app.services.registered_businesses import search_registered
from app.services.secrets_box import decrypt

router = APIRouter(prefix="/outbound", tags=["outbound"])

ET = ZoneInfo("America/New_York")
PT = ZoneInfo("America/Los_Angeles")


def _ready(s) -> bool:
    return bool(s and s["retell_api_key_enc"] and s["retell_agent_id"] and s["from_number"])


def _within_hours(start: str, end: str) -> bool:
    """Weekdays only, and inside the window in EVERY US time zone (west coast >= start, east coast <= end)."""
    now_et = datetime.now(ET)
    return now_et.weekday() < 5 and datetime.now(PT).strftime("%H:%M") >= start and now_et.strftime("%H:%M") <= end


# ── Intent ───────────────────────────────────────────────────────────────────
class IntentReq(BaseModel):
    message: str


@router.post("/intent")
def intent(p: IntentReq, org: Organisation = Depends(get_current_org), db: Session = Depends(get_db)):
    result = detect_outbound_intent(p.message)
    s = _row(db, org.id)
    result["ready"] = _ready(s)
    result["test_mode"] = s["test_mode"] if s else True
    return result


# ── Search registered businesses ─────────────────────────────────────────────
class SearchReq(BaseModel):
    business_type: str = ""
    city: str = ""
    count: int = 5


@router.post("/search")
def search(p: SearchReq, org: Organisation = Depends(get_current_org), db: Session = Depends(get_db)):
    s = _row(db, org.id)
    test_mode = s["test_mode"] if s else True

    # In test mode calls only go to your test numbers, so your own business may appear (handy for a demo).
    leads = search_registered(db, org.id, p.business_type, p.city, p.count, include_self=test_mode)
    matched = True
    if not leads and (p.business_type or p.city):
        leads = search_registered(db, org.id, "", "", p.count, include_self=test_mode)
        matched = False   # nothing matched the filters: show registered businesses instead

    return {"leads": leads, "matched": matched, "ready": _ready(s), "test_mode": test_mode}


# ── Call ─────────────────────────────────────────────────────────────────────
class Lead(BaseModel):
    org_id: str = ""
    name: str = ""
    phone: str
    address: str = ""
    website: str = ""


class CallReq(BaseModel):
    leads: list[Lead]
    notes: str = ""


@router.post("/call")
def call(p: CallReq, org: Organisation = Depends(get_current_org), db: Session = Depends(get_db)):
    s = _row(db, org.id)
    if not _ready(s):
        raise HTTPException(400, "Voice agent is not set up. Go to Settings, then Voice agent.")
    try:
        api_key = decrypt(s["retell_api_key_enc"])
    except Exception:
        raise HTTPException(400, "Saved Retell API key can't be read. Enter it again in settings.")

    test_mode = s["test_mode"]
    test_numbers = [n for n in (s["test_numbers"] or "").split(",") if n]
    if test_mode and not test_numbers:
        raise HTTPException(400, "Test mode is on but no test numbers are saved. Add your own number in settings.")
    if not test_mode and not _within_hours(s["calling_start"], s["calling_end"]):
        raise HTTPException(400, f"Outside calling hours ({s['calling_start']} to {s['calling_end']}, US weekdays).")

    results = []
    for i, lead in enumerate(p.leads[: s["max_calls_per_run"]]):
        item = {"name": lead.name or "Business", "phone": lead.phone, "ok": False}

        try:
            lead_phone = to_e164_us(lead.phone)
        except ValueError as e:
            if not test_mode:
                item["error"] = f"{e} (live calls are US numbers only)"
                results.append(item)
                continue
            lead_phone = re.sub(r"[^\d+]", "", lead.phone)[:20] or "unknown"   # test mode: number is only recorded

        if not test_mode:
            recent = db.execute(
                text("SELECT 1 FROM outbound_calls WHERE org_id = :org AND lead_phone = :p "
                     "AND status <> 'failed' AND created_at > now() - interval '30 days' LIMIT 1"),
                {"org": org.id, "p": lead_phone},
            ).first()
            if recent:
                item["error"] = "Already called in the last 30 days."
                results.append(item)
                continue

        dialed = test_numbers[i % len(test_numbers)] if test_mode else lead_phone
        row_id = db.execute(
            text(
                """
                INSERT INTO outbound_calls
                  (org_id, lead_org_id, business_name, lead_phone, dialed_number, address, website, test_redirect)
                VALUES (:org, CAST(NULLIF(:lead_org, '') AS uuid), :name, :lead, :dialed, :addr, :web, :test)
                RETURNING id::text
                """
            ),
            {"org": org.id, "lead_org": lead.org_id, "name": lead.name, "lead": lead_phone, "dialed": dialed,
             "addr": lead.address, "web": lead.website, "test": test_mode},
        ).scalar()
        db.commit()

        try:
            data = retell_outbound.create_call(
                api_key, s["retell_agent_id"], s["from_number"], dialed,
                variables={
                    "business_name": lead.name,
                    "business_address": lead.address,
                    "pitch": s["pitch"] or "",
                    "caller_company": getattr(org, "name", "") or "",
                    "call_notes": p.notes,
                },
                metadata={"org_id": str(org.id), "call_row_id": row_id, "lead_phone": lead_phone,
                          "lead_org_id": lead.org_id},
            )
            db.execute(
                text("UPDATE outbound_calls SET retell_call_id = :cid, status = :st WHERE id = CAST(:id AS uuid)"),
                {"cid": data.get("call_id"), "st": data.get("call_status") or "registered", "id": row_id},
            )
            item.update(ok=True, status=data.get("call_status") or "registered")
        except Exception as e:
            print("[OUTBOUND CALL] failed:", e)
            db.execute(
                text("UPDATE outbound_calls SET status = 'failed', error = :err WHERE id = CAST(:id AS uuid)"),
                {"err": str(e)[:500], "id": row_id},
            )
            item["error"] = str(e)
        db.commit()
        results.append(item)

    return {"results": results, "test_mode": test_mode}


@router.get("/calls")
def calls(org: Organisation = Depends(get_current_org), db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            "SELECT id::text AS id, business_name, lead_phone, status, error, summary, qualified, "
            "test_redirect, created_at FROM outbound_calls WHERE org_id = :org "
            "ORDER BY created_at DESC LIMIT 50"
        ),
        {"org": org.id},
    ).mappings().all()
    return [{**dict(r), "created_at": r["created_at"].isoformat()} for r in rows]
