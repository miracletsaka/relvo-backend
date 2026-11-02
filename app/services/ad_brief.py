import random
from app.ai.model_client import generate_json

LAYOUTS = {"left-stack": "left half", "bottom-band": "bottom third", "top-band": "top third"}
MOODS = {"bold", "luxury", "playful", "clean"}

SYSTEM = """You are an ad creative director. Create a brief for a 1080x1350 social ad.
Return JSON with exactly these keys:
{"headline":"","subheadline":"","description":"","product_name":"","campaign_label":"",
"cta_text":"","offer_value":"","offer_label":"","price_label":"",
"mood":"bold|luxury|playful|clean","palette":["#bg1","#bg2","#accent"],
"scene":"background visual only"}
Rules:
- headline: max 6 words, punchy.
- Copy price and offer exactly as the user wrote them. Leave empty if not given.
- palette: 3 hex colors that fit the brand and mood.
- scene: describe a background image for the product or service. No text, no logos."""


def build_brief(prompt: str) -> dict:
    data = generate_json(prompt, SYSTEM, fast=True, temperature=0.8, max_output_tokens=1500)
    if not data.get("headline"):
        raise ValueError("Model returned no headline")

    if data.get("mood") not in MOODS:
        data["mood"] = "clean"
    palette = data.get("palette")
    if not isinstance(palette, list) or len(palette) < 3:
        data["palette"] = ["#111827", "#1f2937", "#C9A84C"]

    layout = random.choice(list(LAYOUTS))
    data["layout"] = layout
    data["muse_prompt"] = (
        f"{data.get('scene') or 'abstract premium gradient background'}. "
        f"Color palette: {', '.join(data['palette'])}. "
        f"Professional advertising photography, portrait 4:5. "
        f"Keep the {LAYOUTS[layout]} calm, simple and uncluttered. "
        f"Absolutely no text, letters, numbers, logos or watermarks."
    )
    return data