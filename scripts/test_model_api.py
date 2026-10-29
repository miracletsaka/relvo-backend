import json
import os

import requests
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.ai.model_client import generate_text, generate_json

url = os.getenv("MODEL_API_BASE_URL", "https://api.meta.ai/v1").rstrip("/") + "/responses"
raw = requests.post(
    url,
    headers={"Authorization": f"Bearer {os.getenv('MODEL_API_KEY')}", "Content-Type": "application/json"},
    json={"model": os.getenv("MODEL_NAME", "muse-spark-1.1"), "stream": False,
          "input": [{"role": "user", "content": [{"type": "input_text", "text": "Say hi in 5 words."}]}]},
    timeout=60,
)
print("STATUS:", raw.status_code)
print("RAW:", json.dumps(raw.json(), indent=2)[:1500])
print("\nTEXT:", generate_text("Say hi in 5 words.", system="You are concise."))
print("JSON:", generate_json('Return {"ok": true, "word": "hello"}'))