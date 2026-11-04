"""
Mic transcription proxy. The browser never sees the ASR API key.

    POST /ai-chat/asr-ticket   logged-in users get a one-time ticket (60s)
    WS   /ai-chat/asr?ticket=  relays 24 kHz PCM audio to the ASR service

Register in main.py:
    from app.routers import ai_asr
    app.include_router(ai_asr.router)
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import time
import uuid

import websockets
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket

from app.dependencies.org import get_current_org
from app.models.organisation import Organisation

router = APIRouter(prefix="/ai-chat", tags=["ai-chat-asr"])

ASR_BASE = "wss://api.meta.ai/v1/asr/realtime"
MAX_SESSION_SECONDS = 90

# In-memory tickets. Fine for one Render instance; use Redis if you scale out.
_TICKETS: dict[str, float] = {}


def _issue_ticket() -> str:
    now = time.time()
    for k in [k for k, exp in _TICKETS.items() if exp < now]:
        _TICKETS.pop(k, None)
    t = secrets.token_urlsafe(24)
    _TICKETS[t] = now + 60
    return t


def _consume_ticket(t: str) -> bool:
    exp = _TICKETS.pop(t, 0)
    return exp > time.time()


@router.post("/asr-ticket")
def asr_ticket(org: Organisation = Depends(get_current_org)):
    if not os.environ.get("MODEL_API_KEY") or not os.environ.get("ASR_MODEL"):
        raise HTTPException(503, "Voice input is not configured on the server.")
    return {"ticket": _issue_ticket()}


@router.websocket("/asr")
async def asr_proxy(ws: WebSocket, ticket: str = Query("")):
    if not _consume_ticket(ticket):
        await ws.close(code=4401)
        return
    await ws.accept()

    api_key = os.environ["MODEL_API_KEY"]
    model = os.environ["ASR_MODEL"]
    uri = f"{ASR_BASE}?sessionId=mic-{uuid.uuid4()}"

    try:
        async with websockets.connect(uri, open_timeout=30) as up:
            await up.send(json.dumps({
                "authorization": {"accessToken": f"Bearer {api_key}"},
                "audioEncoding": "PCM_24KHZ",
                "model": model,
                "mode": "PUSH_TO_TALK",
                "partialMode": "CUMULATIVE",
                "emitAudioProgress": False,
            }))
            handshake = json.loads(await up.recv())
            if "sessionId" not in handshake:
                await ws.send_json({"type": "error", "message": "Voice service handshake failed."})
                return
            await ws.send_json({"type": "ready"})

            async def up_to_client():
                async for msg in up:
                    if isinstance(msg, bytes):
                        continue
                    await ws.send_text(msg)

            async def client_to_up():
                while True:
                    msg = await ws.receive()
                    if msg["type"] == "websocket.disconnect":
                        return
                    if msg.get("bytes"):
                        await up.send(msg["bytes"])
                    elif msg.get("text"):
                        await up.send(msg["text"])

            tasks = [asyncio.create_task(up_to_client()), asyncio.create_task(client_to_up())]
            done, pending = await asyncio.wait(
                tasks, timeout=MAX_SESSION_SECONDS, return_when=asyncio.FIRST_COMPLETED
            )
            for t in pending:
                t.cancel()
            for t in done:
                exc = t.exception()
                if exc:
                    print("[ASR] relay error:", exc)
    except Exception as e:
        print("[ASR] failed:", e)
        try:
            await ws.send_json({"type": "error", "message": "Voice input failed. Try again."})
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass