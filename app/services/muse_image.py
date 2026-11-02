import os
import requests

URL = "https://api.meta.ai/v1/responses"


def generate_background(prompt: str) -> str | None:
    """Returns a data URL, or None on any failure (frontend falls back)."""
    key = os.getenv("MODEL_API_KEY")
    if not key:
        return None
    payload = {
        "input": [{
            "role": "user", "type": "message",
            "content": [{"type": "input_text", "text": prompt}],
        }],
        "model": "muse-image-1.0",
        "max_output_tokens": 2048,
        "store": False,
        "stream": False,
        "tools": [{"type": "image_generation", "output_format": "png",
                   "reasoning_strength": "low"}],
    }
    try:
        r = requests.post(URL, headers={"Authorization": f"Bearer {key}"},
                          json=payload, timeout=120)
        r.raise_for_status()
        for item in r.json().get("output", []):
            if item.get("type") == "image_generation_call" and item.get("result"):
                return "data:image/png;base64," + item["result"]
    except Exception as e:
        print("Muse failed:", e)
    return None