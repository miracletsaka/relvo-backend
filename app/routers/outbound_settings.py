"""
Voice-agent settings for outbound calls (one row per organisation).

    GET  /outbound/settings        masked settings (the API key is never returned)
    PUT  /outbound/settings        save (blank api_key = keep the saved one)
    POST /outbound/settings/test   checks the key, agent id and from number against Retell

Register in main.py:
    from app.routers import outbound_settings
    app.include_router(outbound_settings.router)
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.org import get_current_org
from app.models.organisation import Organisation
from app.services import retell_outbound
from app.services.secrets_box import decrypt, encrypt

router = APIRouter(prefix="/outbound/settings", tags=["outbound"])


def to_e164_us(value: str) -> str:
    """'(415) 555-0123' -> '+14155550123'. US numbers only for now."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 10:
        digits = "1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    raise ValueError(f"'{value}' is not a valid US phone number")


def _row(db: Session, org_id):
    return db.execute(
        text("SELECT * FROM voice_settings WHERE org_id = :org"), {"org": org_id}
    ).mappings().first()


def _public(row) -> dict:
    if not row:
        return {
            "api_key_set": False, "key_hint": "", "agent_id": "", "from_number": "", "pitch": "",
            "test_mode": True, "test_numbers": [], "calling_start": "09:00", "calling_end": "17:00",
            "max_calls_per_run": 5, "ready": False,
        }
    hint = ""
    if row["retell_api_key_enc"]:
        try:
            hint = decrypt(row["retell_api_key_enc"])[-4:]
        except Exception:
            hint = ""
    return {
        "api_key_set": bool(row["retell_api_key_enc"]),
        "key_hint": hint,
        "agent_id": row["retell_agent_id"] or "",
        "from_number": row["from_number"] or "",
        "pitch": row["pitch"] or "",
        "test_mode": row["test_mode"],
        "test_numbers": [n for n in (row["test_numbers"] or "").split(",") if n],
        "calling_start": row["calling_start"],
        "calling_end": row["calling_end"],
        "max_calls_per_run": row["max_calls_per_run"],
        "ready": bool(row["retell_api_key_enc"] and row["retell_agent_id"] and row["from_number"]),
    }


@router.get("")
def get_settings(org: Organisation = Depends(get_current_org), db: Session = Depends(get_db)):
    return _public(_row(db, org.id))


class SettingsReq(BaseModel):
    api_key: str = ""              # blank = keep the saved key
    agent_id: str = ""
    from_number: str = ""
    pitch: str = ""
    test_mode: bool = True
    test_numbers: list[str] = []
    calling_start: str = "09:00"
    calling_end: str = "17:00"
    max_calls_per_run: int = 5


@router.put("")
def save_settings(p: SettingsReq, org: Organisation = Depends(get_current_org), db: Session = Depends(get_db)):
    try:
        from_number = to_e164_us(p.from_number) if p.from_number.strip() else ""
        test_numbers = [to_e164_us(n) for n in p.test_numbers if n.strip()]
    except ValueError as e:
        raise HTTPException(400, str(e))

    for t in (p.calling_start, p.calling_end):
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", t):
            raise HTTPException(400, "Calling hours must look like 09:00.")
    if not 1 <= p.max_calls_per_run <= 20:
        raise HTTPException(400, "Max calls per run must be between 1 and 20.")

    key_enc = encrypt(p.api_key.strip()) if p.api_key.strip() else None

    db.execute(
        text(
            """
            INSERT INTO voice_settings
              (org_id, retell_api_key_enc, retell_agent_id, from_number, pitch, test_mode,
               test_numbers, calling_start, calling_end, max_calls_per_run, updated_at)
            VALUES
              (:org, :key, :agent, :from_number, :pitch, :test_mode,
               :test_numbers, :start, :end, :max_calls, now())
            ON CONFLICT (org_id) DO UPDATE SET
              retell_api_key_enc = COALESCE(EXCLUDED.retell_api_key_enc, voice_settings.retell_api_key_enc),
              retell_agent_id = EXCLUDED.retell_agent_id,
              from_number = EXCLUDED.from_number,
              pitch = EXCLUDED.pitch,
              test_mode = EXCLUDED.test_mode,
              test_numbers = EXCLUDED.test_numbers,
              calling_start = EXCLUDED.calling_start,
              calling_end = EXCLUDED.calling_end,
              max_calls_per_run = EXCLUDED.max_calls_per_run,
              updated_at = now()
            """
        ),
        {
            "org": org.id, "key": key_enc, "agent": p.agent_id.strip(), "from_number": from_number,
            "pitch": p.pitch.strip(), "test_mode": p.test_mode, "test_numbers": ",".join(test_numbers),
            "start": p.calling_start, "end": p.calling_end, "max_calls": p.max_calls_per_run,
        },
    )
    db.commit()
    return _public(_row(db, org.id))


@router.post("/test")
def test_settings(org: Organisation = Depends(get_current_org), db: Session = Depends(get_db)):
    row = _row(db, org.id)
    if not row or not row["retell_api_key_enc"] or not row["retell_agent_id"] or not row["from_number"]:
        raise HTTPException(400, "Save the API key, agent ID and from number first.")
    try:
        key = decrypt(row["retell_api_key_enc"])
    except Exception:
        raise HTTPException(400, "Saved API key can't be read. Enter it again and save.")

    agent_ok, agent_msg = retell_outbound.check_agent(key, row["retell_agent_id"])
    number_ok, number_msg = retell_outbound.check_number(key, row["from_number"]) if agent_ok else (False, "Skipped")
    return {
        "ok": agent_ok and number_ok,
        "agent": {"ok": agent_ok, "message": agent_msg},
        "number": {"ok": number_ok, "message": number_msg},
    }