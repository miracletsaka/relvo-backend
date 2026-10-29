"""
backend/app/ai/model_client.py

Single entry point for every text-model call in the backend.
Talks to Meta Model API using the Responses format (POST /v1/responses).

Env vars (backend/.env):
    MODEL_API_KEY            required
    MODEL_API_BASE_URL       default https://api.meta.ai/v1
    MODEL_NAME               default muse-spark-1.1
    MODEL_NAME_FAST          default = MODEL_NAME
    MODEL_REASONING_EFFORT   default "low" (set empty to use the API default)
    MODEL_API_TIMEOUT        default 60 (seconds)
"""
import json
import os
import re
import time

import requests


class ModelAPIError(RuntimeError):
    pass


# ── Config (read at call time, so .env load order never matters) ─────────────
def _config() -> dict:
    key = os.getenv("MODEL_API_KEY")
    if not key:
        raise ModelAPIError("MODEL_API_KEY is not set")

    default_model = os.getenv("MODEL_NAME", "muse-spark-1.1")
    base = os.getenv("MODEL_API_BASE_URL", "https://api.meta.ai/v1").rstrip("/")

    return {
        "key": key,
        "url": f"{base}/responses",
        "model": default_model,
        "fast_model": os.getenv("MODEL_NAME_FAST") or default_model,
        "timeout": float(os.getenv("MODEL_API_TIMEOUT", "60")),
        # "low" keeps hidden thinking cheap. The API default is "high".
        "reasoning_effort": os.getenv("MODEL_REASONING_EFFORT", "low"),
    }


# ── Request building ─────────────────────────────────────────────────────────
def _item(role: str, text: str) -> dict:
    kind = "output_text" if role == "assistant" else "input_text"
    return {"role": role, "content": [{"type": kind, "text": text}]}


def _payload_variants(model, messages, temperature, max_output_tokens, reasoning_effort):
    """Yield payloads from most to least featureful until one is accepted."""
    base = {"model": model, "stream": False}
    items = [_item(m["role"], m["content"]) for m in messages]

    def build(use_temp, use_cap, use_reasoning, input_items):
        payload = {**base, "input": input_items}
        if use_temp and temperature is not None:
            payload["temperature"] = temperature
        if use_cap and max_output_tokens:
            payload["max_output_tokens"] = max_output_tokens
        if use_reasoning and reasoning_effort:
            payload["reasoning"] = {"effort": reasoning_effort}
        return payload

    yield "full", build(True, True, True, items)
    yield "no-temperature", build(False, True, True, items)
    yield "no-token-cap", build(False, False, True, items)
    yield "bare", build(False, False, False, items)

    # Last resort: fold the system prompt into the first user message
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    rest = [m for m in messages if m["role"] != "system"]
    if system and rest:
        merged = [dict(m) for m in rest]
        merged[0]["content"] = f"{system}\n\n---\n\n{merged[0]['content']}"
        yield "system-merged", build(
            False, False, False, [_item(m["role"], m["content"]) for m in merged]
        )


def _post(payload: dict, cfg: dict) -> requests.Response:
    resp = None
    for attempt in range(3):
        resp = requests.post(
            cfg["url"],
            headers={
                "Authorization": f"Bearer {cfg['key']}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=cfg["timeout"],
        )
        if resp.status_code in (429, 502, 503, 504) and attempt < 2:
            time.sleep(1.5 * (attempt + 1))
            continue
        break
    return resp


# ── Response parsing ─────────────────────────────────────────────────────────
def extract_text(data: dict) -> str:
    """Pull the assistant text out of a Responses-format reply (reasoning items are skipped)."""
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"].strip()

    parts = []
    for item in data.get("output") or []:
        if item.get("type") == "message":
            for block in item.get("content") or []:
                if block.get("type") in ("output_text", "text") and block.get("text"):
                    parts.append(block["text"])
    if parts:
        return "".join(parts).strip()

    # Last resort: chat-completions shaped reply
    try:
        return (data["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        return ""


# ── Public API ───────────────────────────────────────────────────────────────
def generate_from_messages(
    messages: list[dict],
    *,
    fast: bool = False,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> str:
    """messages = [{"role": "system"|"user"|"assistant", "content": "text"}, ...]"""
    cfg = _config()
    model = cfg["fast_model"] if fast else cfg["model"]
    last_error = ""

    for name, payload in _payload_variants(
        model, messages, temperature, max_output_tokens, cfg["reasoning_effort"]
    ):
        resp = _post(payload, cfg)

        if resp.status_code == 400:
            last_error = resp.text[:300]
            print(f"[MODEL] 400 with '{name}' payload: {last_error}")
            continue

        if not resp.ok:
            raise ModelAPIError(f"{resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        text = extract_text(data)

        usage = data.get("usage") or {}
        reasoning_tokens = (usage.get("output_tokens_details") or {}).get("reasoning_tokens")
        print(
            f"[MODEL] {model} variant={name} in={usage.get('input_tokens')} "
            f"out={usage.get('output_tokens')} reasoning={reasoning_tokens}"
        )

        if text:
            return text

        if data.get("status") == "incomplete":
            # The token cap was used up by thinking. Retry with fewer constraints.
            last_error = f"incomplete: {data.get('incomplete_details')}"
            continue

        raise ModelAPIError(f"Empty model response: {str(data)[:300]}")

    raise ModelAPIError(f"All variants failed. Last error: {last_error}")


def generate_text(
    user: str,
    system: str | None = None,
    *,
    fast: bool = False,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    return generate_from_messages(
        messages,
        fast=fast,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )


def parse_json(raw: str) -> dict:
    """Tolerates ```json fences and text around the JSON object."""
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return {}


def generate_json(
    user: str,
    system: str | None = None,
    *,
    fast: bool = True,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
) -> dict:
    system = (system or "") + "\n\nReturn ONLY one valid JSON object. No markdown, no commentary."
    raw = generate_text(
        user,
        system.strip(),
        fast=fast,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
    return parse_json(raw)