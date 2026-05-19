"""
backend/app/services/premium_segment_blueprints.py
─────────────────────────────────────────────────────────────────────────────
Tone-aware premium segment blueprints.

Every tone has its own set of design variants per segment type.
The design language for each tone is derived from real reference images:

  advertise  → Image 1 (Nike-style): full-bleed action photo, 2-line bold
               ALL-CAPS headline ON the image, near-zero body copy.
               Image 3 (magazine cover): image fills canvas, brand name in
               isolated dark strip at the bottom, almost no text.
               → Rule: typography dominates, text is minimal and punchy.

  story      → Image 2 (gallery editorial): portrait photo bleeds top section,
               clean white/light panel below, large serif headline, short body
               paragraph, date + category tag below.
               → Rule: editorial text panel rhythm with media handled separately,
                 hierarchy: headline > body > metadata.

Variants within each tone give variety while staying true to the tone's
design language. Blueprint shapes use:

  "__BRAND_ACCENT__"  — replaced with brand.primary_color at assembly
  slotKey             — reserved for separate media/logo engines, not used in text-only segment blueprints
  dataField + text="" — filled by getShapeText() at render time

Canvas base: 1080px wide. Heights defined per segment type.
"""

from typing import Any, Dict, List, Optional

PAD = 56  # base edge padding


# ── Shared shape builders ──────────────────────────────────────────────────────

def _txt(id_, df, x, y, w, h, fs, ff, fw, tc, ta="left", lh=1.0, ls=0, z=5, **kw):
    return {
        "id": id_, "type": "text",
        "x": x, "y": y, "width": w, "height": h,
        "dataField": df, "text": "",
        "fontSize": fs, "fontFamily": ff, "fontWeight": fw,
        "textColor": tc, "textAlign": ta, "lineHeight": lh,
        "letterSpacing": ls, "padding": 8,
        "zIndex": z, "opacity": 1,
        "backgroundColor": "transparent", "borderColor": "transparent",
        "borderWidth": 0, "shadowBlur": 0, "shadowX": 0, "shadowY": 0,
        "shadowColor": "#000000", **kw,
    }


def _rect(id_, x, y, w, h, bg, r=0, z=3, op=1, **kw):
    return {
        "id": id_, "type": "rounded-rect",
        "x": x, "y": y, "width": w, "height": h,
        "backgroundColor": bg, "borderRadius": r,
        "zIndex": z, "opacity": op,
        "borderColor": "transparent", "borderWidth": 0,
        "shadowBlur": 0, "shadowX": 0, "shadowY": 0, "shadowColor": "#000000",
        **kw,
    }


def _circle(id_, x, y, size, bg, z=2, op=1.0):
    return {
        "id": id_, "type": "circle",
        "x": x, "y": y, "width": size, "height": size,
        "backgroundColor": bg, "zIndex": z, "opacity": op,
        "borderColor": "transparent", "borderWidth": 0,
        "shadowBlur": 0, "shadowX": 0, "shadowY": 0, "shadowColor": "#000000",
    }


def _img(id_, sk, x, y, w, h, fit="cover", r=0, z=4):
    return {
        "id": id_, "type": "image",
        "x": x, "y": y, "width": w, "height": h,
        "slotKey": sk,
        "slotLabel": sk.replace("_", " ").title(),
        "slotType": "logo" if sk == "logo" else "image",
        "slotRole": "logo" if sk == "logo" else "hero",
        "fit": fit, "radius": r,
        "slotVisibleWhenEmpty": sk == "logo",
        "src": None, "zIndex": z, "opacity": 1,
        "backgroundColor": "transparent", "borderColor": "transparent",
        "borderWidth": 0, "shadowBlur": 0, "shadowX": 0, "shadowY": 0,
        "shadowColor": "#000000",
    }


def _grad(id_, x, y, w, h, stops, angle=180, r=0, z=5, op=1):
    return {
        "id": id_, "type": "gradient-overlay",
        "x": x, "y": y, "width": w, "height": h,
        "gradientColors": stops, "gradientAngle": angle,
        "backgroundColor": "transparent", "borderWidth": 0,
        "zIndex": z, "opacity": op,
    }


def _grad_rect(id_, x, y, w, h, stops, angle=90, r=0, z=3, op=1, **kw):
    return {
        "id": id_, "type": "rounded-rect",
        "x": x, "y": y, "width": w, "height": h,
        "backgroundColor": "transparent",
        "gradientColors": stops,
        "gradientAngle": angle,
        "borderRadius": r, "zIndex": z, "opacity": op,
        "borderColor": "transparent", "borderWidth": 0,
        "shadowBlur": 0, "shadowX": 0, "shadowY": 0, "shadowColor": "#000000",
        **kw,
    }


A   = "__BRAND_ACCENT__"
DK  = "#05070b"
BLK = "#000000"
WHT = "#ffffff"

_FADE_DOWN  = [{"stop": 0, "color": "rgba(0,0,0,0)"}, {"stop": 1, "color": "rgba(0,0,0,0.88)"}]
_FADE_UP    = [{"stop": 0, "color": "rgba(0,0,0,0.88)"}, {"stop": 1, "color": "rgba(0,0,0,0)"}]
_FADE_HALF  = [{"stop": 0, "color": "rgba(0,0,0,0)"}, {"stop": 1, "color": "rgba(0,0,0,0.70)"}]
_FADE_HARD  = [{"stop": 0, "color": "rgba(0,0,0,0)"}, {"stop": 1, "color": "rgba(0,0,0,0.96)"}]


# ══════════════════════════════════════════════════════════════════════════════
#  ADVERTISE TONE
#  Design language: typography-led impact, minimal text, bold impact headline
#  ON the image. Text almost never lives below the image.
#  Ref: Image 1 (Nike athletic) + Image 3 (magazine cover / brand name only)
# ══════════════════════════════════════════════════════════════════════════════

# ── HERO — 430px ──────────────────────────────────────────────────────────────

ADVERTISE_HERO: List[List[Dict]] = [

    # A: Full-bleed image, oversized 2-line hook top-left on scrim, no body copy
    # Ref: Image 1 — "ENGINEERED / FOR IMPACT." directly on action photo
    [
        _grad("ah-a-scrim", 0, 140, 1080, 290, _FADE_HARD, 180, z=3),
        _grad("ah-a-scrim-l", 0, 0, 400, 430,
              [{"stop":0,"color":"rgba(0,0,0,0.55)"},{"stop":1,"color":"rgba(0,0,0,0)"}], 90, z=3),
        _txt("ah-a-hook", "hook", PAD, 220, 600, 200, 96, "Bebas Neue", 900, WHT, "left", 0.88, -1, z=10),
    ],

    # B: Image fills canvas, brand/CTA sits in isolated black strip at bottom
    # Ref: Image 3 — magazine cover, "DREAMCORE" in black panel below image
    [
        _rect("ah-b-panel", 0, 360, 1080, 70, BLK, 0, z=3),
        _txt("ah-b-hook",    "hook",     PAD, 372, 700, 52, 38, "Bebas Neue", 900, WHT,    "left",   1.0, 4,  z=10),
        _txt("ah-b-cta",     "cta_text", 800, 372, 224, 52, 28, "Bebas Neue", 700, A,      "right",  1.0, 2,  z=10),
    ],

    # C: Image right 60%, deep left scrim, single massive hook word, accent bar
    [
        _grad("ah-c-scrim", 0, 0, 560, 430,
              [{"stop":0,"color":"rgba(0,0,0,0.95)"},{"stop":1,"color":"rgba(0,0,0,0)"}], 90, z=3),
        _rect("ah-c-bar", 0, 0, 8, 430, A, 0, z=4),
        _txt("ah-c-hook", "hook", PAD+18, 110, 480, 220, 100, "Bebas Neue", 900, WHT, "left", 0.87, -2, z=10),
        _txt("ah-c-cta",  "cta_text", PAD+18, 340, 380, 56, 28, "Bebas Neue", 700, A, "left", 1.0, 2, z=10),
    ],

    # D: Full bleed, hook bottom-left two lines, CTA pill bottom-right
    [
        _grad("ah-d-bot", 0, 240, 1080, 190, _FADE_HARD, 180, z=3),
        _grad("ah-d-top", 0, 0,   1080, 100, _FADE_UP,   180, z=3),
        _txt("ah-d-hook", "hook", PAD, 280, 660, 150, 82, "Bebas Neue", 900, WHT, "left", 0.88, -1, z=10),
        _rect("ah-d-cta-bg", 740, 350, 280, 58, A, 999, z=10,
              shadowBlur=20, shadowX=0, shadowY=6, shadowColor="rgba(0,0,0,0.5)"),
        _txt("ah-d-cta",  "cta_text", 756, 362, 248, 36, 26, "Bebas Neue", 800, WHT, "center", 1.0, 1, z=11),
    ],
]


# ── CTA — 160px ───────────────────────────────────────────────────────────────

ADVERTISE_CTA: List[List[Dict]] = [

    # A: Full-width accent bar, hook-sized CTA text inside it, near zero copy
    [
        _rect("ac-a-bg", 0, 0, 1080, 160, BLK, 0, z=0),
        _grad_rect("ac-a-bar", PAD, 34, 968, 82,
                   [{"stop":0,"color":A},{"stop":1,"color":"rgba(0,0,0,0.5)"}], 135, r=4, z=4),
        _txt("ac-a-cta", "cta_text", PAD+24, 52, 920, 48, 36, "Bebas Neue", 900, WHT, "center", 1.0, 3, z=5),
    ],

    # B: Minimal — accent dot + single CTA line, nothing else
    [
        _rect("ac-b-bg", 0, 0, 1080, 160, BLK, 0, z=0),
        _circle("ac-b-dot", PAD, 70, 18, A, z=4),
        _txt("ac-b-cta",   "cta_text", PAD+32, 58, 760, 56, 42, "Bebas Neue", 900, WHT, "left",   1.0, 2, z=5),
        _txt("ac-b-proof", "proof",    860,     70, 164, 36, 18, "Syne",       500, A,   "right",  1.0, 0, z=5),
    ],

    # C: Image strip behind CTA, heavy scrim
    [
        _grad("ac-c-scrim", 0, 0, 1080, 160,
              [{"stop":0,"color":"rgba(0,0,0,0.7)"},{"stop":1,"color":"rgba(0,0,0,0.9)"}], 90, z=3),
        _txt("ac-c-cta",   "cta_text", PAD, 52, 680, 60, 42, "Bebas Neue", 900, WHT,    "left",  1.0, 2, z=5),
        _txt("ac-c-proof", "proof",    PAD, 112, 600, 36, 18, "Syne",      400, "rgba(255,255,255,0.50)", "left", 1.0, 0, z=5),
    ],

    # D: Right-aligned CTA, accent underline only decoration
    [
        _rect("ac-d-bg", 0, 0, 1080, 160, BLK, 0, z=0),
        _rect("ac-d-line", PAD, 0, 968, 3, A, 0, z=2),
        _txt("ac-d-cta",   "cta_text", 0, 50, 1024, 60, 44, "Bebas Neue", 900, WHT, "right", 1.0, 2, z=5),
        _txt("ac-d-proof", "proof",    0, 112, 1024, 34, 18, "Syne",      400, "rgba(255,255,255,0.45)", "right", 1.0, 0, z=5),
    ],
]


# ── REVIEW — 260px ────────────────────────────────────────────────────────────

ADVERTISE_REVIEW: List[List[Dict]] = [

    # A: Single bold quote line, no author body — impact style
    [
        _rect("ar-a-bg", 0, 0, 1080, 260, BLK, 0, z=0),
        _txt("ar-a-text",   "review_text",   PAD, 52,  900, 120, 48, "Bebas Neue", 900, WHT, "left", 0.90, -1, z=5),
        _txt("ar-a-author", "review_author", PAD, 180, 420,  48, 24, "Syne",       500, A,   "left", 1.0,  1,  z=5),
        _txt("ar-a-rating", "review_rating", PAD, 224,  200,  34, 22, "Syne",      400, A,   "left", 1.0,  2,  z=5),
    ],

    # B: Quote on image with heavy scrim
    [
        _grad("ar-b-scrim", 0, 0, 1080, 260,
              [{"stop":0,"color":"rgba(0,0,0,0.5)"},{"stop":1,"color":"rgba(0,0,0,0.92)"}], 180, z=3),
        _txt("ar-b-text",   "review_text",   PAD, 36,  900, 130, 36, "Bebas Neue", 700, WHT, "left", 0.94, 0,  z=5),
        _txt("ar-b-author", "review_author", PAD, 178, 400,  46, 22, "Syne",       600, A,   "left", 1.0,  1,  z=5),
        _txt("ar-b-rating", "review_rating", PAD, 222, 180,  32, 20, "Syne",       400, A,   "left", 1.0,  2,  z=5),
    ],

    # C: Left accent bar, minimal — just quote + author
    [
        _rect("ar-c-bg",  0, 0, 1080, 260, DK, 0, z=0),
        _rect("ar-c-bar", 0, 0, 6, 260, A, 0, z=2),
        _txt("ar-c-text",   "review_text",   PAD+18, 48,  900, 130, 38, "Bebas Neue", 700, WHT, "left", 0.93, -1, z=5),
        _txt("ar-c-author", "review_author", PAD+18, 192, 400,  46, 22, "Syne",       500, A,   "left", 1.0,  1,  z=5),
        _txt("ar-c-rating", "review_rating", PAD+18, 228, 180,  30, 20, "Syne",       400, A,   "left", 1.0,  2,  z=5),
    ],

    # D: Full-width, quote centred, author bottom-right
    [
        _rect("ar-d-bg",   0,   0, 1080, 260, BLK, 0, z=0),
        _rect("ar-d-rule", PAD, 0, 968, 4, A, 0, z=2),
        _txt("ar-d-text",   "review_text",   PAD, 24,  968, 140, 40, "Bebas Neue", 700, WHT,    "center", 0.93, -1, z=5),
        _txt("ar-d-author", "review_author", 540, 188, 480,  46, 22, "Syne",       500, A,      "right",  1.0,  1,  z=5),
        _txt("ar-d-rating", "review_rating", PAD, 196, 300,  40, 22, "Syne",       400, A,      "left",   1.0,  2,  z=5),
    ],
]


# ── FOOTER — 190px ────────────────────────────────────────────────────────────

ADVERTISE_FOOTER: List[List[Dict]] = [
    [
        _rect("af-a-bg", 0, 0, 1080, 190, BLK, 0, z=0),
        _rect("af-a-line", PAD, 0, 968, 3, A, 0, z=2),
        _txt("af-a-row1", "contact_row1", PAD, 54, 650, 34, 20, "Syne", 600, "rgba(255,255,255,0.72)", "left", 1.0, 0, z=5),
        _txt("af-a-row2", "contact_row2", PAD, 98, 650, 30, 16, "Syne", 400, "rgba(255,255,255,0.45)", "left", 1.0, 0, z=5),
        _txt("af-a-web", "business_website", 760, 76, 264, 34, 20, "Syne", 700, A, "right", 1.0, 0, z=5),
    ],
    [
        _rect("af-b-bg", 0, 0, 1080, 190, DK, 0, z=0),
        _rect("af-b-left", 0, 0, 6, 190, A, 0, z=2),
        _txt("af-b-row1", "contact_row1", PAD + 18, 52, 720, 34, 19, "Syne", 600, "rgba(255,255,255,0.70)", "left", 1.0, 0, z=5),
        _txt("af-b-row2", "contact_row2", PAD + 18, 94, 720, 30, 15, "Syne", 400, "rgba(255,255,255,0.42)", "left", 1.0, 0, z=5),
        _txt("af-b-web", "business_website", PAD + 18, 132, 420, 30, 17, "Syne", 700, A, "left", 1.0, 0, z=5),
    ],
    [
        _rect("af-c-bg", 0, 0, 1080, 190, BLK, 0, z=0),
        _rect("af-c-rule", PAD, 38, 968, 1, "rgba(255,255,255,0.12)", 0, z=2),
        _txt("af-c-row1", "contact_row1", PAD, 66, 968, 34, 20, "Syne", 600, "rgba(255,255,255,0.72)", "center", 1.0, 0, z=5),
        _txt("af-c-row2", "contact_row2", PAD, 106, 968, 30, 15, "Syne", 400, "rgba(255,255,255,0.42)", "center", 1.0, 0, z=5),
        _txt("af-c-web", "business_website", PAD, 140, 968, 30, 17, "Syne", 700, A, "center", 1.0, 0, z=5),
    ],
]


ADVERTISE_OFFER: List[List[Dict]] = [

    # A: Image fills right, price dominates left — product ad
    [
        _grad("ao-a-scrim", 440, 0, 200, 300,
              [{"stop":0,"color":"rgba(0,0,0,0)"},{"stop":1,"color":"rgba(0,0,0,1)"}], 90, z=3),
        _rect("ao-a-bg", 0, 0, 560, 300, BLK, 0, z=1),
        _txt("ao-a-title", "offer_title", PAD, 28,  500, 110, 66, "Bebas Neue", 900, WHT, "left", 0.90, -1, z=5),
        _txt("ao-a-price", "price",       PAD, 148, 400, 110, 86, "Bebas Neue", 900, A,   "left", 0.88, -2, z=5),
        _txt("ao-a-label", "discount_label", PAD, 262, 380, 46, 22, "Syne", 600, A, "left", 1.2, 1.5, z=5),
    ],

    # B: Full-bleed image, price badge bottom-left
    [
        _grad("ao-b-bot", 0, 140, 1080, 160, _FADE_HARD, 180, z=3),
        _rect("ao-b-badge", PAD, 196, 280, 88, A, 6, z=6,
              shadowBlur=20, shadowX=0, shadowY=6, shadowColor="rgba(0,0,0,0.5)"),
        _txt("ao-b-price",  "price",       PAD+14, 202, 252, 74, 56, "Bebas Neue", 900, WHT, "center", 0.90, -1, z=7),
        _txt("ao-b-title",  "offer_title", PAD,    290, 500,  50, 30, "Syne",       600, WHT, "left",   1.0,  1,  z=6),
    ],

    # C: Diagonal price band across dark canvas
    [
        _rect("ao-c-bg", 0, 0, 1080, 300, DK, 0, z=0),
        _grad_rect("ao-c-band", 0, 80, 1080, 140,
                   [{"stop":0,"color":A},{"stop":1,"color":"rgba(0,0,0,0.5)"}], 90, z=3, op=0.90),
        _txt("ao-c-title", "offer_title", PAD, 24,  700, 50, 30, "Syne",       600, "rgba(255,255,255,0.65)", "left", 1.0, 1, z=5),
        _txt("ao-c-price", "price",       PAD, 88,  500, 120, 92, "Bebas Neue", 900, WHT, "left", 0.87, -3, z=6),
        _txt("ao-c-label", "discount_label", PAD, 230, 360, 50, 24, "Syne", 700, WHT, "left", 1.2, 2, z=5),
    ],

    # D: Minimal — price large, label small, nothing else
    [
        _rect("ao-d-bg",   0, 0, 1080, 300, BLK, 0, z=0),
        _rect("ao-d-rule", PAD, 0, 968, 4, A, 0, z=2),
        _txt("ao-d-title", "offer_title",    PAD,  14, 700, 50, 28, "Syne",       600, "rgba(255,255,255,0.55)", "left", 1.0, 2, z=5),
        _txt("ao-d-price", "price",          PAD,  62, 560, 130, 104,"Bebas Neue", 900, WHT, "left", 0.86, -4, z=6),
        _txt("ao-d-label", "discount_label", PAD, 204, 400,  52, 26, "Syne",       700, A,   "left", 1.2,  2,  z=5),
    ],
]


# ── FEATURE LIST — 340px ──────────────────────────────────────────────────────

ADVERTISE_FEATURES: List[List[Dict]] = [

    # A: Bold headline, 4 features as short punchy lines with accent markers
    [
        _rect("afl-a-bg", 0, 0, 1080, 340, BLK, 0, z=0),
        _txt("afl-a-head", "headline", PAD, 26, 860, 80, 56, "Bebas Neue", 900, WHT, "left", 0.92, -1, z=5),
        _rect("afl-a-rule", PAD, 112, 80, 5, A, 999, z=4),
        *[s for i in range(1,5) for s in [
            _rect(f"afl-a-m{i}", PAD, 128+(i-1)*54+16, 14, 14, A, 999, z=4),
            _txt(f"afl-a-f{i}", f"feature_{i}", PAD+28, 128+(i-1)*54, 840, 50, 28, "Syne", 500,
                 "rgba(255,255,255,0.82)", "left", 1.2, 0, z=5),
        ]],
    ],

    # B: 2-column punchy features, big headline
    [
        _rect("afl-b-bg", 0, 0, 1080, 340, DK, 0, z=0),
        _txt("afl-b-head", "headline", PAD, 22, 860, 80, 54, "Bebas Neue", 900, WHT, "left", 0.93, -1, z=5),
        *[s for i,(x,y) in enumerate([(PAD,116),(560,116),(PAD,204),(560,204)],1) for s in [
            _rect(f"afl-b-a{i}", x, y+14, 6, 30, A, 999, z=4),
            _txt(f"afl-b-f{i}", f"feature_{i}", x+18, y, 450, 50, 26, "Syne", 500,
                 "rgba(255,255,255,0.80)", "left", 1.2, 0, z=5),
        ]],
    ],

    # C: Features as large numbered Bebas lines
    [
        _rect("afl-c-bg", 0, 0, 1080, 340, BLK, 0, z=0),
        _txt("afl-c-head", "headline", PAD, 18, 860, 76, 52, "Bebas Neue", 900, WHT, "left", 0.93, 0, z=5),
        *[s for i in range(1,5) for s in [
            _txt(f"afl-c-n{i}", "deco_icon", PAD, 104+(i-1)*58, 52, 50, 38, "Bebas Neue", 900, A, "left", 1.0, 0, z=4),
            _txt(f"afl-c-f{i}", f"feature_{i}", PAD+60, 104+(i-1)*58, 800, 50, 26, "Syne", 500,
                 "rgba(255,255,255,0.80)", "left", 1.2, 0, z=5),
            _rect(f"afl-c-sep{i}", PAD+60, 150+(i-1)*58, 800, 1, "rgba(255,255,255,0.07)", 0, z=3),
        ]],
    ],

    # D: Image right, feature list left — product sell-in ad
    [
        _grad("afl-d-scrim", 460, 0, 200, 340,
              [{"stop":0,"color":"rgba(0,0,0,0)"},{"stop":1,"color":"rgba(0,0,0,1)"}], 90, z=3),
        _rect("afl-d-bg", 0, 0, 560, 340, BLK, 0, z=1),
        _txt("afl-d-head", "headline", PAD, 20, 500, 72, 48, "Bebas Neue", 900, WHT, "left", 0.93, -1, z=5),
        *[_txt(f"afl-d-f{i}", f"feature_{i}", PAD, 100+(i-1)*58, 500, 50, 24, "Syne", 500,
               "rgba(255,255,255,0.78)", "left", 1.2, 0, z=5) for i in range(1,5)],
    ],
]


# ── HEADLINE — 260px ──────────────────────────────────────────────────────────

ADVERTISE_HEADLINE: List[List[Dict]] = [

    # A: Image fills canvas, hook on scrim — pure impact ad
    [
        _grad("ahl-a-scrim", 0, 60, 1080, 200, _FADE_HARD, 180, z=3),
        _txt("ahl-a-hook", "hook", PAD, 140, 860, 120, 78, "Bebas Neue", 900, WHT, "left", 0.88, -2, z=10),
    ],

    # B: Black, oversized hook, accent underline only
    [
        _rect("ahl-b-bg", 0, 0, 1080, 260, BLK, 0, z=0),
        _txt("ahl-b-hook", "hook",       PAD, PAD, 880, 150, 86, "Bebas Neue", 900, WHT, "left", 0.90, -2, z=5),
        _rect("ahl-b-rule",PAD, 204, 100, 6, A, 999, z=4),
        _txt("ahl-b-sub",  "subheading", PAD, 214, 700,  56, 26, "Syne",       400, "rgba(255,255,255,0.58)", "left", 1.3, 0, z=5),
    ],

    # C: Left accent bar, hook right-shifted
    [
        _rect("ahl-c-bg",  0, 0, 1080, 260, DK, 0, z=0),
        _rect("ahl-c-bar", 0, 0, 8, 260, A, 0, z=2),
        _txt("ahl-c-hook", "hook",       PAD+18, PAD, 860, 150, 88, "Bebas Neue", 900, WHT, "left", 0.89, -2, z=5),
        _txt("ahl-c-sub",  "subheading", PAD+18, 208, 700,  52, 26, "Syne",       400, "rgba(255,255,255,0.56)", "left", 1.3, 0, z=5),
    ],

    # D: Centred hook, accent dot above — poster style
    [
        _rect("ahl-d-bg",  0, 0, 1080, 260, BLK, 0, z=0),
        _circle("ahl-d-dot", 506, 32, 68, A, z=3, op=0.22),
        _txt("ahl-d-hook", "hook",       PAD, 54, 880, 150, 82, "Bebas Neue", 900, WHT, "center", 0.90, -1, z=5),
        _txt("ahl-d-sub",  "subheading", PAD, 210, 880,  56, 26, "Syne",       400, "rgba(255,255,255,0.55)", "center", 1.3, 0, z=5),
    ],
]


# ── REVIEW/SPONSOR — short ────────────────────────────────────────────────────

ADVERTISE_SPONSOR: List[List[Dict]] = [

    # A: Label + 4 logo slots, black, minimal
    [
        _rect("asp-a-bg", 0, 0, 1080, 170, BLK, 0, z=0),
        _txt("asp-a-label", "proof", PAD, 14, 968, 30, 18, "Syne", 500, "rgba(255,255,255,0.28)", "center", 1.0, 3, z=5),
        *[_img(f"asp-a-l{i}", f"sponsor_{i}", PAD+(i-1)*236, 52, 196, 90, fit="contain", r=0, z=4) for i in range(1,5)],
    ],

    # B: Accent rule above logos
    [
        _rect("asp-b-bg",   0, 0, 1080, 170, DK, 0, z=0),
        _rect("asp-b-rule", PAD, 16, 968, 4, A, 999, z=3),
        _txt("asp-b-label", "proof", PAD, 28, 968, 28, 17, "Syne", 400, "rgba(255,255,255,0.25)", "center", 1.0, 3, z=5),
        *[_img(f"asp-b-l{i}", f"sponsor_{i}", PAD+(i-1)*236, 60, 196, 86, fit="contain", r=0, z=4) for i in range(1,5)],
    ],

    # C: Dark pill containers
    [
        _rect("asp-c-bg", 0, 0, 1080, 170, BLK, 0, z=0),
        _txt("asp-c-label", "proof", PAD, 12, 968, 28, 17, "Syne", 400, "rgba(255,255,255,0.25)", "center", 1.0, 3, z=5),
        *[s for i in range(1,5) for s in [
            _rect(f"asp-c-box{i}", PAD+(i-1)*238, 48, 200, 96, "rgba(255,255,255,0.04)", 10, z=3),
            _img(f"asp-c-l{i}", f"sponsor_{i}", PAD+(i-1)*238+10, 58, 180, 76, fit="contain", r=0, z=4),
        ]],
    ],

    # D: Full-bleed image, logos over scrim
    [
        _rect("asp-d-ov", 0, 0, 1080, 170, "rgba(0,0,0,0.82)", 0, z=3),
        _txt("asp-d-label", "proof", PAD, 10, 968, 28, 17, "Syne", 400, "rgba(255,255,255,0.35)", "center", 1.0, 3, z=5),
        *[_img(f"asp-d-l{i}", f"sponsor_{i}", PAD+(i-1)*236, 46, 196, 92, fit="contain", r=0, z=4) for i in range(1,5)],
    ],
]


# ══════════════════════════════════════════════════════════════════════════════
#  STORY TONE
#  Design language: image fills top section, clean editorial panel below,
#  headline uses serif-weight, short body paragraph, date/category metadata.
#  Ref: Image 2 — gallery editorial with white/light panel below portrait.
#  Rule: text never overlaps image. Generous white space. Hierarchy over impact.
# ══════════════════════════════════════════════════════════════════════════════

# ── HERO — 430px ──────────────────────────────────────────────────────────────

STORY_HERO: List[List[Dict]] = [

    # A: Portrait bleeds top 260px, white/dark text panel below — exact Image 2 rhythm
    [
        _rect("sh-a-panel", 0, 260, 1080, 170, DK, 0, z=3),
        _txt("sh-a-hook", "hook",       PAD, 272, 880, 120, 52, "Syne",       700, WHT, "left", 1.08, -0.5, z=5),
        _txt("sh-a-sub",  "subheading", PAD, 398, 760,  50, 22, "Syne",       400, "rgba(255,255,255,0.60)", "left", 1.45, 0, z=5),
    ],

    # B: Image top 300px, narrow editorial strip below, date-style label
    [
        _rect("sh-b-strip", 0, 300, 1080, 130, DK, 0, z=3),
        _rect("sh-b-rule",  PAD, 300, 80, 3, A, 0, z=4),
        _txt("sh-b-hook", "hook",       PAD, 310, 800, 90, 44, "Syne",       700, WHT, "left", 1.10, -0.5, z=5),
        _txt("sh-b-sub",  "subheading", PAD, 408, 680,  40, 20, "Syne",       400, "rgba(255,255,255,0.55)", "left", 1.5, 0, z=5),
    ],

    # C: Image fills entire canvas, white text panel anchored to bottom
    [
        _rect("sh-c-panel", 0, 300, 1080, 130, "rgba(4,6,10,0.94)", 0, z=4),
        _txt("sh-c-hook", "hook",       PAD, 308, 800, 90, 44, "Syne",       700, WHT, "left", 1.1,  -0.5, z=5),
        _txt("sh-c-sub",  "subheading", PAD, 404, 680,  40, 20, "Syne",       400, "rgba(255,255,255,0.60)", "left", 1.5, 0, z=5),
    ],

    # D: Side-by-side — image left 50%, editorial right panel
    [
        _grad("sh-d-scrim", 400, 0, 200, 430,
              [{"stop":0,"color":"rgba(5,7,11,0)"},{"stop":1,"color":"rgba(5,7,11,1)"}], 90, z=3),
        _rect("sh-d-panel", 540, 0, 540, 430, DK, 0, z=3),
        _txt("sh-d-hook", "hook",       560, 60,  460, 240, 52, "Syne",       700, WHT, "left", 1.08, -0.5, z=5),
        _txt("sh-d-sub",  "subheading", 560, 310, 460,  80, 20, "Syne",       400, "rgba(255,255,255,0.58)", "left", 1.5, 0, z=5),
        _txt("sh-d-cta",  "cta_text",   560, 398, 300,  40, 18, "Syne",       600, A,   "left", 1.0, 1, z=5),
    ],
]


# ── CTA — 160px ───────────────────────────────────────────────────────────────

STORY_CTA: List[List[Dict]] = [

    # A: Editorial CTA — underlined link style, no heavy button
    [
        _rect("sc-a-bg", 0, 0, 1080, 160, DK, 0, z=0),
        _rect("sc-a-line", PAD, 0, 968, 2, "rgba(255,255,255,0.12)", 0, z=2),
        _txt("sc-a-cta",   "cta_text", PAD, 44, 600, 60, 32, "Syne", 600, WHT, "left",  1.0, -0.5, z=5),
        _rect("sc-a-ul",   PAD, 106, 400, 2, A, 0, z=4),
        _txt("sc-a-proof", "proof",    PAD, 114, 700, 38, 17, "Syne", 400, "rgba(255,255,255,0.45)", "left", 1.5, 0, z=5),
    ],

    # B: Outlined soft button, proof line below
    [
        _rect("sc-b-bg", 0, 0, 1080, 160, DK, 0, z=0),
        _rect("sc-b-btn", PAD, 34, 380, 66, "transparent", 6, z=4, borderColor=A, borderWidth=2),
        _txt("sc-b-cta",   "cta_text", PAD+18, 50, 344, 36, 26, "Syne", 600, A,   "center", 1.0, -0.5, z=5),
        _txt("sc-b-proof", "proof",    PAD+4,  110, 700, 38, 17, "Syne", 400, "rgba(255,255,255,0.45)", "left", 1.5, 0, z=5),
    ],

    # C: Image strip behind, soft scrim, editorial CTA
    [
        _grad("sc-c-scrim", 0, 0, 1080, 160,
              [{"stop":0,"color":"rgba(4,6,10,0.65)"},{"stop":1,"color":"rgba(4,6,10,0.90)"}], 90, z=3),
        _txt("sc-c-cta",   "cta_text", PAD, 42, 600, 60, 32, "Syne", 600, WHT, "left", 1.0, -0.5, z=5),
        _txt("sc-c-proof", "proof",    PAD, 108, 700, 38, 17, "Syne", 400, "rgba(255,255,255,0.50)", "left", 1.5, 0, z=5),
    ],

    # D: Accent top rule, text only — no button at all
    [
        _rect("sc-d-bg",   0, 0, 1080, 160, DK, 0, z=0),
        _rect("sc-d-rule", 0, 0, 1080, 3, A, 0, z=2),
        _txt("sc-d-cta",   "cta_text", PAD, 46, 750, 62, 36, "Syne", 700, WHT, "left", 1.0, -0.5, z=5),
        _txt("sc-d-arr",   "proof",    820, 56, 204, 44, 22, "Syne", 500, A,   "right", 1.0, 1, z=5),
    ],
]


# ── REVIEW — 260px ────────────────────────────────────────────────────────────

STORY_REVIEW: List[List[Dict]] = [

    # A: Editorial — serif italic quote, author below in small caps style
    [
        _rect("sr-a-bg",  0, 0, 1080, 260, DK, 0, z=0),
        _rect("sr-a-rule",PAD-6, PAD-6, 6, 140, A, 2, z=3),
        _txt("sr-a-text",   "review_text",   PAD+10, PAD, 860, 140, 28,
             "Georgia, serif", 400, "rgba(255,255,255,0.88)", "left", 1.60, 0, z=5, fontStyle="italic"),
        _txt("sr-a-author", "review_author", PAD,    190, 500,  46, 20, "Syne", 600, WHT, "left", 1.0, 2, z=5),
        _txt("sr-a-rating", "review_rating", PAD,    230, 200,  32, 20, "Syne", 400, A,   "left", 1.0, 2, z=5),
    ],

    # B: Image top strip, quote below — story rhythm
    [
        _rect("sr-b-panel", 0, 100, 1080, 160, DK, 0, z=3),
        _txt("sr-b-text",   "review_text",   PAD, 108, 880, 110, 26,
             "Georgia, serif", 400, "rgba(255,255,255,0.88)", "left", 1.55, 0, z=5, fontStyle="italic"),
        _txt("sr-b-author", "review_author", PAD, 226, 400,  36, 18, "Syne", 600, WHT, "left", 1.0, 1, z=5),
        _txt("sr-b-rating", "review_rating", 500, 228, 300,  34, 18, "Syne", 400, A,   "right",1.0, 2, z=5),
    ],

    # C: Wide card with accent border, generous padding
    [
        _rect("sr-c-bg",   0,   0, 1080, 260, DK, 0, z=0),
        _rect("sr-c-card", PAD-16, 18, 1048, 224, "rgba(255,255,255,0.03)", 14, z=3, borderColor=A, borderWidth=1),
        _txt("sr-c-text",   "review_text",   PAD+8, 38, 860, 130, 26,
             "Georgia, serif", 400, "rgba(255,255,255,0.88)", "left", 1.58, 0, z=5, fontStyle="italic"),
        _txt("sr-c-author", "review_author", PAD+8, 178, 440,  44, 18, "Syne", 600, WHT, "left", 1.0, 1, z=5),
        _txt("sr-c-rating", "review_rating", PAD+8, 218, 200,  36, 18, "Syne", 400, A,   "left", 1.0, 2, z=5),
    ],

    # D: No card — thin rule, quote text, author right-aligned
    [
        _rect("sr-d-bg",   0,   0, 1080, 260, DK, 0, z=0),
        _txt("sr-d-text",  "review_text",   PAD, PAD, 880, 140, 28,
             "Georgia, serif", 400, "rgba(255,255,255,0.88)", "left", 1.58, 0, z=5, fontStyle="italic"),
        _rect("sr-d-rule", PAD, 188, 900, 2, A, 999, z=3),
        _txt("sr-d-author","review_author", PAD, 196, 500,  44, 18, "Syne", 600, WHT,  "left",  1.0, 1, z=5),
        _txt("sr-d-rating","review_rating", 700, 200, 324,  44, 18, "Syne", 400, A,    "right", 1.0, 2, z=5),
    ],
]


# ── FOOTER — 190px ────────────────────────────────────────────────────────────

STORY_FOOTER: List[List[Dict]] = [
    [
        _rect("sft-a-bg", 0, 0, 1080, 190, DK, 0, z=0),
        _rect("sft-a-rule", PAD, 0, 968, 1, "rgba(255,255,255,0.14)", 0, z=2),
        _txt("sft-a-row1", "contact_row1", PAD, 56, 650, 34, 17, "Syne", 400, "rgba(255,255,255,0.62)", "left", 1.4, 0, z=5),
        _txt("sft-a-row2", "contact_row2", PAD, 96, 650, 30, 14, "Syne", 400, "rgba(255,255,255,0.38)", "left", 1.4, 0, z=5),
        _txt("sft-a-web", "business_website", 690, 76, 334, 34, 16, "Syne", 600, A, "right", 1.0, 0, z=5),
    ],
    [
        _rect("sft-b-bg", 0, 0, 1080, 190, "#030507", 0, z=0),
        _rect("sft-b-top", 0, 0, 1080, 2, A, 0, z=1),
        _rect("sft-b-mid", 0, 94, 1080, 1, "rgba(255,255,255,0.07)", 0, z=1),
        _txt("sft-b-row1", "contact_row1", PAD, 20, 640, 34, 18, "Syne", 400, "rgba(255,255,255,0.65)", "left", 1.4, 0, z=5),
        _txt("sft-b-row2", "contact_row2", PAD, 56, 640, 28, 14, "Syne", 400, "rgba(255,255,255,0.38)", "left", 1.4, 0, z=5),
        _txt("sft-b-web", "business_website", PAD, 110, 500, 32, 16, "Syne", 600, A, "left", 1.0, 0, z=5),
    ],
    [
        _rect("sft-c-bg", 0, 0, 1080, 190, DK, 0, z=0),
        _rect("sft-c-accent", 0, 0, 4, 190, A, 0, z=1),
        _txt("sft-c-row1", "contact_row1", PAD + 14, 52, 720, 34, 17, "Syne", 500, "rgba(255,255,255,0.60)", "left", 1.4, 0, z=5),
        _txt("sft-c-row2", "contact_row2", PAD + 14, 92, 720, 28, 14, "Syne", 400, "rgba(255,255,255,0.36)", "left", 1.4, 0, z=5),
        _txt("sft-c-web", "business_website", 640, 82, 384, 34, 16, "Syne", 600, A, "right", 1.0, 0, z=5),
    ],
]


STORY_OFFER: List[List[Dict]] = [

    # A: Image top, editorial price/offer below — magazine product feature
    [
        _rect("sof-a-panel", 0, 160, 1080, 140, DK, 0, z=3),
        _rect("sof-a-rule",  PAD, 160, 80, 3, A, 0, z=4),
        _txt("sof-a-title", "offer_title",    PAD, 170, 640, 76, 38, "Syne",       700, WHT, "left", 1.0,  -0.5, z=5),
        _txt("sof-a-price", "price",          680, 160, 344, 96, 72, "Bebas Neue", 900, A,   "right", 0.88, -1,  z=5),
        _txt("sof-a-label", "discount_label", PAD, 254, 400, 44, 18, "Syne",       500, "rgba(255,255,255,0.55)", "left", 1.0, 1.5, z=5),
    ],

    # B: Editorial two-column — text left, price right
    [
        _rect("sof-b-bg", 0, 0, 1080, 300, DK, 0, z=0),
        _txt("sof-b-title", "offer_title",       PAD, 36,  500, 110, 42, "Syne",       700, WHT, "left", 1.05, -0.5, z=5),
        _txt("sof-b-desc",  "offer_description", PAD, 154, 500, 80, 20, "Syne",       400, "rgba(255,255,255,0.58)", "left", 1.5, 0, z=5),
        _txt("sof-b-label", "discount_label",    PAD, 240, 380, 44, 18, "Syne",       600, A,   "left", 1.0, 1.5, z=5),
        _rect("sof-b-div", 560, 36, 1, 240, "rgba(255,255,255,0.10)", 0, z=3),
        _txt("sof-b-price", "price",             580, 60,  440, 130, 88, "Bebas Neue", 900, A,   "center", 0.87, -2, z=5),
        _txt("sof-b-comp",  "compare_at_price",  580, 196, 440,  60, 24, "Syne",       400, "rgba(255,255,255,0.40)", "center", 1.2, 0, z=5),
    ],

    # C: Clean white-card style on dark — product detail panel
    [
        _rect("sof-c-bg",   0,   0, 1080, 300, DK, 0, z=0),
        _rect("sof-c-card", PAD-16, 18, 1048, 264, "rgba(255,255,255,0.04)", 14, z=3, borderColor="rgba(255,255,255,0.10)", borderWidth=1),
        _txt("sof-c-title", "offer_title",       PAD+8, 34, 700, 90, 40, "Syne", 700, WHT, "left", 1.05, -0.5, z=5),
        _txt("sof-c-desc",  "offer_description", PAD+8, 130, 700, 76, 19, "Syne", 400, "rgba(255,255,255,0.56)", "left", 1.5, 0, z=5),
        _txt("sof-c-price", "price",             800, 34, 232, 110, 76, "Bebas Neue", 900, A,   "right", 0.87, -2, z=5),
        _txt("sof-c-label", "discount_label",    PAD+8, 214, 380, 44, 17, "Syne", 500, A,   "left",  1.0, 1.5, z=5),
    ],

    # D: Metadata row style — small label, big title, price inline
    [
        _rect("sof-d-bg",   0, 0, 1080, 300, DK, 0, z=0),
        _txt("sof-d-label", "discount_label",    PAD,  22, 500, 38, 14, "Syne", 600, A,   "left", 1.0, 2.5, z=5),
        _rect("sof-d-rule", PAD, 62, 968, 1, "rgba(255,255,255,0.10)", 0, z=3),
        _txt("sof-d-title", "offer_title",       PAD,  70, 700, 100, 44, "Syne", 700, WHT, "left", 1.05, -0.5, z=5),
        _txt("sof-d-price", "price",             PAD,  178, 420, 106, 84, "Bebas Neue", 900, A, "left", 0.86, -2, z=5),
        _txt("sof-d-comp",  "compare_at_price",  490, 210, 300,  62, 24, "Syne", 400, "rgba(255,255,255,0.38)", "left", 1.2, 0, z=5),
    ],
]


# ── FEATURE LIST — 340px ──────────────────────────────────────────────────────

STORY_FEATURES: List[List[Dict]] = [

    # A: Image top strip, features as readable body below — editorial product story
    [
        _rect("sfl-a-panel", 0, 100, 1080, 240, DK, 0, z=3),
        _txt("sfl-a-head", "headline", PAD, 108, 860, 66, 34, "Syne", 700, WHT, "left", 1.05, -0.5, z=5),
        *[_txt(f"sfl-a-f{i}", f"feature_{i}", PAD, 182+(i-1)*42, 860, 40, 18, "Syne", 400,
               "rgba(255,255,255,0.70)", "left", 1.4, 0, z=5) for i in range(1,5)],
    ],

    # B: Editorial list — headline + 4 lines, serif-weight header, thin dividers
    [
        _rect("sfl-b-bg", 0, 0, 1080, 340, DK, 0, z=0),
        _txt("sfl-b-head", "headline", PAD, 28, 860, 66, 36, "Syne", 700, WHT, "left", 1.05, -0.5, z=5),
        _rect("sfl-b-rule",PAD, 100, 968, 1, "rgba(255,255,255,0.12)", 0, z=3),
        *[s for i in range(1,5) for s in [
            _txt(f"sfl-b-f{i}", f"feature_{i}", PAD, 110+(i-1)*56, 840, 48, 20, "Syne", 400,
                 "rgba(255,255,255,0.70)", "left", 1.4, 0, z=5),
            _rect(f"sfl-b-d{i}", PAD, 154+(i-1)*56, 968, 1, "rgba(255,255,255,0.07)", 0, z=3),
        ]],
    ],

    # C: Two-column readable grid
    [
        _rect("sfl-c-bg", 0, 0, 1080, 340, DK, 0, z=0),
        _txt("sfl-c-head","headline", PAD, 24, 860, 66, 34, "Syne", 700, WHT, "left", 1.05, -0.5, z=5),
        *[s for i,(x,y,w) in enumerate([(PAD,100,460),(PAD+516,100,460),(PAD,192,460),(PAD+516,192,460)],1) for s in [
            _rect(f"sfl-c-d{i}", x, y, 3, 36, A, 0, z=4),
            _txt(f"sfl-c-f{i}", f"feature_{i}", x+16, y, w-16, 44, 19, "Syne", 400,
                 "rgba(255,255,255,0.70)", "left", 1.35, 0, z=5),
        ]],
        _rect("sfl-c-mv", PAD+508, 96, 1, 200, "rgba(255,255,255,0.08)", 0, z=3),
    ],

    # D: Numbered editorial style
    [
        _rect("sfl-d-bg", 0, 0, 1080, 340, DK, 0, z=0),
        _txt("sfl-d-head","headline", PAD, 22, 860, 66, 34, "Syne", 700, WHT, "left", 1.05, -0.5, z=5),
        *[s for i in range(1,5) for s in [
            _txt(f"sfl-d-n{i}", "deco_icon", PAD, 96+(i-1)*58, 44, 44, 28, "Syne", 700, A, "left", 1.0, 0, z=4),
            _txt(f"sfl-d-f{i}", f"feature_{i}", PAD+56, 96+(i-1)*58, 820, 48, 19, "Syne", 400,
                 "rgba(255,255,255,0.70)", "left", 1.4, 0, z=5),
            _rect(f"sfl-d-r{i}", PAD+56, 140+(i-1)*58, 820, 1, "rgba(255,255,255,0.07)", 0, z=3),
        ]],
    ],
]


# ── HEADLINE — 260px ──────────────────────────────────────────────────────────

STORY_HEADLINE: List[List[Dict]] = [

    # A: Image top, editorial headline below — core Image 2 structure
    [
        _rect("sthl-a-panel",0, 140, 1080, 120, DK, 0, z=3),
        _txt("sthl-a-hook",  "hook",       PAD, 148, 880, 90, 38, "Syne", 700, WHT, "left", 1.08, -0.5, z=5),
        _txt("sthl-a-sub",   "subheading", PAD, 244, 760, 50, 18, "Syne", 400, "rgba(255,255,255,0.55)", "left", 1.5, 0, z=5),
    ],

    # B: Editorial — hook large, small proof tag, accent rule
    [
        _rect("sthl-b-bg",   0, 0, 1080, 260, DK, 0, z=0),
        _txt("sthl-b-hook",  "hook",       PAD, 36,  880, 140, 52, "Syne", 700, WHT, "left", 1.08, -0.5, z=5),
        _rect("sthl-b-rule", PAD, 182, 80, 2, A, 0, z=3),
        _txt("sthl-b-sub",   "subheading", PAD, 190, 760, 56, 18, "Syne", 400, "rgba(255,255,255,0.55)", "left", 1.5, 0, z=5),
        _txt("sthl-b-proof", "proof",      PAD, 218, 500, 34, 14, "Syne", 500, A,   "left", 1.0, 1.5, z=5),
    ],

    # C: Left half image, right half editorial text
    [
        _grad("sthl-c-scrim", 380, 0, 180, 260,
              [{"stop":0,"color":"rgba(5,7,11,0)"},{"stop":1,"color":"rgba(5,7,11,1)"}], 90, z=3),
        _rect("sthl-c-panel", 520, 0, 560, 260, DK, 0, z=3),
        _txt("sthl-c-hook",  "hook",       540, 36,  500, 140, 40, "Syne", 700, WHT, "left", 1.08, -0.5, z=5),
        _txt("sthl-c-sub",   "subheading", 540, 184, 500, 56, 17, "Syne", 400, "rgba(255,255,255,0.55)", "left", 1.5, 0, z=5),
    ],

    # D: Metadata-style with date/tag — Image 2 bottom row style
    [
        _rect("sthl-d-bg",   0, 0, 1080, 260, DK, 0, z=0),
        _txt("sthl-d-proof", "proof",      PAD, 28, 500, 32, 14, "Syne", 500, A,   "left", 1.0, 2, z=5),
        _rect("sthl-d-rule", PAD, 62, 968, 1, "rgba(255,255,255,0.12)", 0, z=3),
        _txt("sthl-d-hook",  "hook",       PAD, 74,  880, 130, 46, "Syne", 700, WHT, "left", 1.08, -0.5, z=5),
        _txt("sthl-d-sub",   "subheading", PAD, 210, 760, 50, 17, "Syne", 400, "rgba(255,255,255,0.55)", "left", 1.5, 0, z=5),
    ],
]


# ── SPONSOR — 170px ───────────────────────────────────────────────────────────

STORY_SPONSOR: List[List[Dict]] = [

    # A: Editorial — thin top rule, logos on dark, small label
    [
        _rect("ssp-a-bg",   0, 0, 1080, 170, DK, 0, z=0),
        _rect("ssp-a-rule", PAD, 14, 968, 1, "rgba(255,255,255,0.14)", 0, z=2),
        _txt("ssp-a-label", "proof", PAD, 22, 968, 28, 14, "Syne", 400, "rgba(255,255,255,0.30)", "center", 1.0, 2.5, z=5),
        *[_img(f"ssp-a-l{i}", f"sponsor_{i}", PAD+(i-1)*236, 56, 196, 88, fit="contain", r=0, z=4) for i in range(1,5)],
    ],

    # B: Card-wrapped logos
    [
        _rect("ssp-b-bg",    0, 0, 1080, 170, DK, 0, z=0),
        _txt("ssp-b-label",  "proof", PAD, 10, 968, 26, 13, "Syne", 400, "rgba(255,255,255,0.28)", "center", 1.0, 2.5, z=5),
        *[s for i in range(1,5) for s in [
            _rect(f"ssp-b-card{i}", PAD+(i-1)*238, 40, 202, 100, "rgba(255,255,255,0.04)", 10, z=3, borderColor="rgba(255,255,255,0.10)", borderWidth=1),
            _img(f"ssp-b-l{i}", f"sponsor_{i}", PAD+(i-1)*238+10, 50, 182, 80, fit="contain", r=0, z=4),
        ]],
    ],

    # C: Accent top bar, logos below
    [
        _rect("ssp-c-bg",    0, 0, 1080, 170, DK, 0, z=0),
        _rect("ssp-c-bar",   0, 0, 1080, 3,  A,  0, z=2),
        _txt("ssp-c-label",  "proof", PAD, 10, 968, 26, 13, "Syne", 400, "rgba(255,255,255,0.28)", "center", 1.0, 2.5, z=5),
        *[_img(f"ssp-c-l{i}", f"sponsor_{i}", PAD+(i-1)*236, 46, 196, 90, fit="contain", r=0, z=4) for i in range(1,5)],
    ],

    # D: Image strip behind, translucent overlay, logos
    [
        _rect("ssp-d-ov", 0, 0, 1080, 170, "rgba(4,6,10,0.85)", 0, z=3),
        _txt("ssp-d-label","proof", PAD, 8, 968, 26, 13, "Syne", 400, "rgba(255,255,255,0.35)", "center", 1.0, 2.5, z=5),
        *[_img(f"ssp-d-l{i}", f"sponsor_{i}", PAD+(i-1)*236, 42, 196, 94, fit="contain", r=0, z=4) for i in range(1,5)],
    ],
]


# ══════════════════════════════════════════════════════════════════════════════
#  REGISTRY
#  Each tone maps segment_type → { height, variants: List[List[Dict]] }
# ══════════════════════════════════════════════════════════════════════════════

_TONE_BLUEPRINTS: Dict[str, Dict[str, Dict[str, Any]]] = {

    "advertise": {
        "hero_image":   {"height": 430, "variants": ADVERTISE_HERO},
        "cta_button":   {"height": 160, "variants": ADVERTISE_CTA},
        "review_block": {"height": 260, "variants": ADVERTISE_REVIEW},
        "footer":       {"height": 190, "variants": ADVERTISE_FOOTER},
        "offer_block":  {"height": 300, "variants": ADVERTISE_OFFER},
        "price_block":  {"height": 300, "variants": ADVERTISE_OFFER},
        "feature_list": {"height": 340, "variants": ADVERTISE_FEATURES},
        "headline":     {"height": 260, "variants": ADVERTISE_HEADLINE},
        "sponsor_bar":  {"height": 170, "variants": ADVERTISE_SPONSOR},
    },

    "story": {
        "hero_image":   {"height": 430, "variants": STORY_HERO},
        "cta_button":   {"height": 160, "variants": STORY_CTA},
        "review_block": {"height": 260, "variants": STORY_REVIEW},
        "footer":       {"height": 190, "variants": STORY_FOOTER},
        "offer_block":  {"height": 300, "variants": STORY_OFFER},
        "price_block":  {"height": 300, "variants": STORY_OFFER},
        "feature_list": {"height": 340, "variants": STORY_FEATURES},
        "headline":     {"height": 260, "variants": STORY_HEADLINE},
        "sponsor_bar":  {"height": 170, "variants": STORY_SPONSOR},
    },
}

# Fallback when tone is unknown — default to advertise
_DEFAULT_TONE = "advertise"


def get_blueprint(
    segment_type: str,
    brand_seed:   int  = 0,
    tone_name:    str  = _DEFAULT_TONE,
) -> Optional[Dict[str, Any]]:
    """
    Returns the shapes + height for a segment type under the given tone.

    brand_seed selects which design variant within the tone:
      - same brand + same tone → same variant (brand consistency)
      - different seed          → different variant (variety across generations)

    Returns None if segment_type is not registered for that tone.
    """
    tone_key  = tone_name.lower().strip() if tone_name else _DEFAULT_TONE
    tone_map  = _TONE_BLUEPRINTS.get(tone_key) or _TONE_BLUEPRINTS[_DEFAULT_TONE]
    entry     = tone_map.get(segment_type)

    if not entry:
        # Try the default tone as fallback before giving up
        entry = _TONE_BLUEPRINTS[_DEFAULT_TONE].get(segment_type)

    if not entry:
        return None

    variants = entry["variants"]
    height   = entry["height"]
    variant  = variants[brand_seed % len(variants)]

    return {
        "segment_type":   segment_type,
        "segment_height": height,
        "shapes":         variant,
        "variant_index":  brand_seed % len(variants),
        "total_variants": len(variants),
        "tone":           tone_key,
    }


def list_segment_types(tone_name: str = _DEFAULT_TONE) -> List[str]:
    tone_key = tone_name.lower().strip()
    return list((_TONE_BLUEPRINTS.get(tone_key) or _TONE_BLUEPRINTS[_DEFAULT_TONE]).keys())


def list_tones() -> List[str]:
    return list(_TONE_BLUEPRINTS.keys())
"""
backend/app/services/premium_segment_blueprints.py
─────────────────────────────────────────────────────────────────────────────
Tone-aware premium segment blueprints.

KEY DESIGN DECISIONS (derived from reference marketing images):
─────────────────────────────────────────────────────────────────────────────

  advertise  → Image 1 (Nike-style): full-bleed action photo, 2-line bold
               ALL-CAPS headline ON the image, ZERO body copy.
               Image 3 (magazine cover): image fills canvas, brand name in
               isolated dark strip at the bottom.

               CRITICAL RULES for advertise:
               - brand_color IS the background (not just an accent stripe)
               - Maximum 2-3 text shapes on canvas — hook + badge only
               - Product image (product_shot slot) is the centrepiece
               - White text on brand-coloured or dark backgrounds
               - No subheading, no description, no proof copy

  story      → Image 2 (gallery editorial): portrait photo top section,
               clean dark panel below, medium-weight headline + short body.
               - Image top half, editorial text panel bottom half
               - More text allowed: headline + 1 subheading + metadata
               - Serif-feel fonts at readable sizes (not 90px)

Shape tokens:
  "__BRAND_ACCENT__"  → replaced with brand.primary_color (used for accents/text)
  "__BRAND_BG__"      → replaced with brand.primary_color (used for full bg fills)
  slotKey             → replaced with actual image URL at render time
  dataField + text="" → filled by getShapeText() at render time
"""

from typing import Any, Dict, List, Optional

PAD = 56


# ── Shape builders ─────────────────────────────────────────────────────────────

def _txt(id_, df, x, y, w, h, fs, ff, fw, tc, ta="left", lh=1.0, ls=0, z=5, **kw):
    return {
        "id": id_, "type": "text",
        "x": x, "y": y, "width": w, "height": h,
        "dataField": df, "text": "",
        "fontSize": fs, "fontFamily": ff, "fontWeight": fw,
        "textColor": tc, "textAlign": ta, "lineHeight": lh,
        "letterSpacing": ls, "padding": 8,
        "zIndex": z, "opacity": 1,
        "backgroundColor": "transparent", "borderColor": "transparent",
        "borderWidth": 0, "shadowBlur": 0, "shadowX": 0, "shadowY": 0,
        "shadowColor": "#000000", **kw,
    }


def _rect(id_, x, y, w, h, bg, r=0, z=3, op=1, **kw):
    return {
        "id": id_, "type": "rounded-rect",
        "x": x, "y": y, "width": w, "height": h,
        "backgroundColor": bg, "borderRadius": r,
        "zIndex": z, "opacity": op,
        "borderColor": "transparent", "borderWidth": 0,
        "shadowBlur": 0, "shadowX": 0, "shadowY": 0, "shadowColor": "#000000",
        **kw,
    }


def _circle(id_, x, y, size, bg, z=2, op=1.0):
    return {
        "id": id_, "type": "circle",
        "x": x, "y": y, "width": size, "height": size,
        "backgroundColor": bg, "zIndex": z, "opacity": op,
        "borderColor": "transparent", "borderWidth": 0,
        "shadowBlur": 0, "shadowX": 0, "shadowY": 0, "shadowColor": "#000000",
    }


def _img(id_, sk, x, y, w, h, fit="cover", r=0, z=4):
    return {
        "id": id_, "type": "image",
        "x": x, "y": y, "width": w, "height": h,
        "slotKey": sk,
        "slotLabel": sk.replace("_", " ").title(),
        "slotType": "logo" if sk == "logo" else "image",
        "slotRole": "logo" if sk == "logo" else ("product" if sk == "product_shot" else "hero"),
        "fit": fit, "radius": r,
        "slotVisibleWhenEmpty": sk in ("logo",),
        "src": None, "zIndex": z, "opacity": 1,
        "backgroundColor": "transparent", "borderColor": "transparent",
        "borderWidth": 0, "shadowBlur": 0, "shadowX": 0, "shadowY": 0,
        "shadowColor": "#000000",
    }


def _grad(id_, x, y, w, h, stops, angle=180, z=5, op=1):
    return {
        "id": id_, "type": "gradient-overlay",
        "x": x, "y": y, "width": w, "height": h,
        "gradientColors": stops, "gradientAngle": angle,
        "backgroundColor": "transparent", "borderWidth": 0,
        "zIndex": z, "opacity": op,
    }


def _grad_rect(id_, x, y, w, h, stops, angle=90, r=0, z=3, op=1, **kw):
    return {
        "id": id_, "type": "rounded-rect",
        "x": x, "y": y, "width": w, "height": h,
        "backgroundColor": "transparent",
        "gradientColors": stops, "gradientAngle": angle,
        "borderRadius": r, "zIndex": z, "opacity": op,
        "borderColor": "transparent", "borderWidth": 0,
        "shadowBlur": 0, "shadowX": 0, "shadowY": 0, "shadowColor": "#000000",
        **kw,
    }


# Token constants
A   = "__BRAND_ACCENT__"   # brand colour used as accent/text/stroke
BG  = "__BRAND_BG__"       # brand colour used as FULL BACKGROUND FILL
DK  = "#05070b"
BLK = "#000000"
WHT = "#ffffff"

# Gradient presets
_FADE_DOWN = [{"stop": 0, "color": "rgba(0,0,0,0)"}, {"stop": 1, "color": "rgba(0,0,0,0.88)"}]
_FADE_HARD = [{"stop": 0, "color": "rgba(0,0,0,0)"}, {"stop": 1, "color": "rgba(0,0,0,0.96)"}]
_FADE_UP   = [{"stop": 0, "color": "rgba(0,0,0,0.85)"}, {"stop": 1, "color": "rgba(0,0,0,0)"}]
_FADE_L    = [{"stop": 0, "color": "rgba(0,0,0,0.90)"}, {"stop": 1, "color": "rgba(0,0,0,0)"}]


# ══════════════════════════════════════════════════════════════════════════════
#  ADVERTISE TONE
#  Rule: brand_color fills the canvas. Product image is centrepiece.
#  Max 2-3 text shapes. Hook is huge (90-110px). No body copy.
#  Reference: Nike poster + MEGA SALE social ads + magazine cover.
# ══════════════════════════════════════════════════════════════════════════════

# ── HERO — 430px ──────────────────────────────────────────────────────────────

ADVERTISE_HERO: List[List[Dict]] = [

    # A: Brand-color bg, product image right, oversized hook left — Nike style
    [
        _rect("ah-a-bg",    0, 0, 1080, 430, BG, 0, z=0),
        _circle("ah-a-c1", 700, -80, 500, "rgba(0,0,0,0.12)", z=1),
        _circle("ah-a-c2", -60, 200, 300, "rgba(255,255,255,0.07)", z=1),
        _grad("ah-a-scrim", 480, 0, 200, 430, _FADE_L, 90, z=4),
        _txt("ah-a-hook", "hook", PAD, 80, 520, 240, 108, "Bebas Neue", 900, WHT, "left", 0.85, -2, z=10),
        _txt("ah-a-badge", "discount_label", PAD, 330, 280, 54, 28, "Bebas Neue", 700, WHT, "left", 1.0, 3, z=10),
    ],

    # B: Black bg, product image fills top-right, white hook large bottom-left — MEGA SALE style
    [
        _rect("ah-b-bg",   0, 0, 1080, 430, BLK, 0, z=0),
        _rect("ah-b-band", 0, 320, 1080, 110, BG, 0, z=1),
        _grad("ah-b-scrim", 440, 0, 200, 430, _FADE_L, 90, z=4),
        _txt("ah-b-hook",  "hook", PAD, 88, 480, 220, 96, "Bebas Neue", 900, WHT, "left", 0.87, -2, z=10),
        _txt("ah-b-badge", "discount_label", PAD, 330, 350, 66, 38, "Bebas Neue", 900, BLK, "left", 1.0, 2, z=10),
    ],

    # C: Split — brand-color left panel, image right, hook white on colour
    [
        _rect("ah-c-col",  0, 0, 560, 430, BG, 0, z=0),
        _rect("ah-c-dark", 560, 0, 520, 430, DK, 0, z=0),
        _grad("ah-c-scrim", 480, 0, 160, 430, _FADE_L, 90, z=4),
        _circle("ah-c-c1", -100, -100, 400, "rgba(255,255,255,0.08)", z=1),
        _txt("ah-c-hook",  "hook", PAD, 90, 480, 230, 100, "Bebas Neue", 900, WHT, "left", 0.86, -2, z=10),
        _txt("ah-c-badge", "discount_label", PAD, 332, 340, 54, 30, "Bebas Neue", 700, WHT, "left", 1.0, 3, z=10),
    ],

    # D: Magazine cover — product fills entire canvas, brand-color bottom strip, minimal text
    [
        _grad("ah-d-bot",  0, 220, 1080, 210, _FADE_HARD, 180, z=3),
        _rect("ah-d-strip",0, 370, 1080, 60, BG, 0, z=3),
        _txt("ah-d-hook",  "hook", PAD, 376, 700, 52, 36, "Bebas Neue", 900, WHT, "left", 1.0, 4, z=10),
        _txt("ah-d-badge", "discount_label", 760, 376, 264, 50, 26, "Bebas Neue", 700, BLK, "right", 1.0, 2, z=10),
    ],
]


# ── CTA — 160px ───────────────────────────────────────────────────────────────

ADVERTISE_CTA: List[List[Dict]] = [

    # A: Brand-color full bg, white CTA text massive, nothing else
    [
        _rect("ac-a-bg",  0, 0, 1080, 160, BG, 0, z=0),
        _circle("ac-a-c", 950, -60, 280, "rgba(0,0,0,0.12)", z=1),
        _txt("ac-a-cta",  "cta_text", PAD, 48, 900, 70, 46, "Bebas Neue", 900, WHT, "left", 1.0, 3, z=5),
        _txt("ac-a-proof","proof", PAD, 118, 600, 34, 18, "Syne", 500, "rgba(255,255,255,0.55)", "left", 1.0, 1, z=5),
    ],

    # B: Black bg, brand-color gradient bar with white CTA inside
    [
        _rect("ac-b-bg",  0, 0, 1080, 160, BLK, 0, z=0),
        _grad_rect("ac-b-bar", PAD, 32, 968, 84,
                   [{"stop":0,"color":BG},{"stop":1,"color":"rgba(0,0,0,0.45)"}], 120, r=6, z=4),
        _txt("ac-b-cta",  "cta_text", PAD+24, 52, 920, 50, 38, "Bebas Neue", 900, WHT, "center", 1.0, 2, z=5),
        _txt("ac-b-proof","proof", PAD, 124, 968, 30, 17, "Syne", 400, "rgba(255,255,255,0.40)", "center", 1.0, 0, z=5),
    ],

    # C: Brand-color top stripe, dark rest, minimal single CTA line
    [
        _rect("ac-c-bg",   0, 0, 1080, 160, DK, 0, z=0),
        _rect("ac-c-bar",  0, 0, 1080, 5, BG, 0, z=2),
        _circle("ac-c-dot",PAD-8, 72, 18, BG, z=3),
        _txt("ac-c-cta",   "cta_text", PAD+28, 50, 800, 64, 48, "Bebas Neue", 900, WHT, "left", 1.0, 2, z=5),
        _txt("ac-c-proof", "proof", 880, 64, 144, 36, 17, "Syne", 500, A, "right", 1.0, 0, z=5),
    ],

    # D: Brand-color right panel, dark left, CTA right-anchored
    [
        _rect("ac-d-dark", 0, 0, 640, 160, DK, 0, z=0),
        _rect("ac-d-col",  640, 0, 440, 160, BG, 0, z=0),
        _txt("ac-d-cta",   "cta_text", PAD, 52, 560, 62, 44, "Bebas Neue", 900, WHT, "left", 1.0, 2, z=5),
        _txt("ac-d-proof", "proof", 660, 58, 360, 48, 22, "Bebas Neue", 700, WHT, "center", 1.0, 1, z=5),
    ],
]


# ── REVIEW — 260px ────────────────────────────────────────────────────────────

ADVERTISE_REVIEW: List[List[Dict]] = [

    # A: Brand-color bg, huge review quote white, author small
    [
        _rect("ar-a-bg", 0, 0, 1080, 260, BG, 0, z=0),
        _circle("ar-a-c", 900, -60, 320, "rgba(0,0,0,0.12)", z=1),
        _txt("ar-a-q",    "deco_icon", PAD-10, PAD-18, 100, 90, 120, "Georgia,serif", 900, "rgba(255,255,255,0.10)", "left", 0.8, 0, z=3),
        _txt("ar-a-text", "review_text", PAD+8, PAD, 900, 140, 36, "Bebas Neue", 700, WHT, "left", 0.93, -1, z=5),
        _txt("ar-a-auth", "review_author", PAD, 186, 500, 46, 22, "Syne", 600, "rgba(255,255,255,0.70)", "left", 1.0, 1, z=5),
        _txt("ar-a-star", "review_rating", PAD, 226, 200, 34, 20, "Syne", 400, "rgba(255,255,255,0.55)", "left", 1.0, 2, z=5),
    ],

    # B: Black, left brand-color bar, Bebas quote
    [
        _rect("ar-b-bg",  0, 0, 1080, 260, BLK, 0, z=0),
        _rect("ar-b-bar", 0, 0, 8, 260, BG, 0, z=2),
        _txt("ar-b-text", "review_text",  PAD+18, 42, 900, 140, 42, "Bebas Neue", 700, WHT, "left", 0.92, -1, z=5),
        _txt("ar-b-auth", "review_author",PAD+18, 192, 500, 46, 22, "Syne", 600, A, "left", 1.0, 1, z=5),
        _txt("ar-b-star", "review_rating",PAD+18, 228, 200, 32, 20, "Syne", 400, A, "left", 1.0, 2, z=5),
    ],

    # C: Brand-color bottom bar, dark top, quote dominant
    [
        _rect("ar-c-dark", 0, 0, 1080, 200, DK, 0, z=0),
        _rect("ar-c-col",  0, 200, 1080, 60, BG, 0, z=0),
        _txt("ar-c-text", "review_text",  PAD, 34, 900, 148, 40, "Bebas Neue", 700, WHT, "left", 0.92, -1, z=5),
        _txt("ar-c-auth", "review_author",PAD, 208, 500, 44, 20, "Syne", 600, BLK, "left", 1.0, 1, z=5),
        _txt("ar-c-star", "review_rating",600, 212, 400, 36, 18, "Syne", 400, BLK, "right", 1.0, 2, z=5),
    ],

    # D: Full brand-color, centred quote, author bottom-right
    [
        _rect("ar-d-bg", 0, 0, 1080, 260, BG, 0, z=0),
        _rect("ar-d-line",PAD, 0, 968, 4, "rgba(255,255,255,0.25)", 0, z=2),
        _txt("ar-d-text", "review_text",  PAD, 22, 968, 148, 38, "Bebas Neue", 700, WHT, "center", 0.92, -1, z=5),
        _txt("ar-d-auth", "review_author",540, 186, 484, 46, 20, "Syne", 600, "rgba(255,255,255,0.70)", "right", 1.0, 1, z=5),
        _txt("ar-d-star", "review_rating",PAD, 192, 300, 40, 20, "Syne", 400, "rgba(255,255,255,0.60)", "left", 1.0, 2, z=5),
    ],
]


# ── FOOTER — 190px ────────────────────────────────────────────────────────────

ADVERTISE_FOOTER: List[List[Dict]] = [

    # A: Brand-color bg, logo + brand name dominant, contact small — magazine strip
    [
        _rect("af-a-bg",  0, 0, 1080, 190, BG, 0, z=0),
        _circle("af-a-c", 960, -80, 300, "rgba(0,0,0,0.10)", z=1),
        _txt("af-a-co",   "companyName",      300,  30, 400, 62, 44, "Bebas Neue", 900, WHT, "left",  1.0, 3, z=5),
        _txt("af-a-web",  "business_website", PAD, 118, 520, 34, 18, "Syne", 600, "rgba(255,255,255,0.65)", "left", 1.0, 0, z=5),
        _txt("af-a-soc",  "social_handle",    560, 118, 464, 34, 20, "Bebas Neue", 700, "rgba(255,255,255,0.70)", "right", 1.0, 1, z=5),
    ],

    # B: Black, brand-color top stripe, content balanced
    [
        _rect("af-b-bg",   0, 0, 1080, 190, BLK, 0, z=0),
        _rect("af-b-top",  0, 0, 1080, 5, BG, 0, z=1),
        _txt("af-b-co",    "companyName",      PAD+158, 30, 380, 54, 38, "Bebas Neue", 900, WHT, "left", 1.0, 3, z=5),
        _txt("af-b-web",   "business_website", PAD, 116, 520, 34, 18, "Syne", 600, A, "left", 1.0, 0, z=5),
        _txt("af-b-soc",   "social_handle",    560, 116, 464, 34, 20, "Bebas Neue", 700, "rgba(255,255,255,0.55)", "right", 1.0, 1, z=5),
    ],

    # C: Brand-color left half, dark right, logo in brand zone
    [
        _rect("af-c-col",  0, 0, 480, 190, BG, 0, z=0),
        _rect("af-c-dark", 480, 0, 600, 190, DK, 0, z=0),
        _txt("af-c-co",    "companyName",      PAD,    92,  380, 54, 34, "Bebas Neue", 900, WHT, "left", 1.0, 3, z=5),
        _txt("af-c-web",   "business_website", 510,    38, 520, 34, 18, "Syne", 600, A, "left", 1.0, 0, z=5),
        _txt("af-c-row1",  "contact_row1",     510,    80, 520, 34, 16, "Syne", 400, "rgba(255,255,255,0.55)", "left", 1.0, 0, z=5),
        _txt("af-c-soc",   "social_handle",    510,   120, 520, 46, 24, "Bebas Neue", 700, "rgba(255,255,255,0.55)", "left", 1.0, 0, z=5),
    ],

    # D: Pure brand-color, company name ultra-large centred — magazine brand strip
    [
        _rect("af-d-bg",  0, 0, 1080, 190, BG, 0, z=0),
        _txt("af-d-co",   "companyName",      0,  18, 1080, 90, 72, "Bebas Neue", 900, WHT, "center", 1.0, 5, z=5),
        _txt("af-d-web",  "business_website", PAD,118, 480, 32, 17, "Syne", 600, "rgba(255,255,255,0.55)", "left", 1.0, 0, z=5),
        _txt("af-d-soc",  "social_handle",    560,118, 464, 32, 21, "Bebas Neue", 700, "rgba(255,255,255,0.65)", "right", 1.0, 0, z=5),
    ],
]


# ── OFFER / PRICE — 300px ─────────────────────────────────────────────────────

ADVERTISE_OFFER: List[List[Dict]] = [

    # A: Brand-color bg, product image right, price huge left — MEGA SALE style
    [
        _rect("ao-a-bg",   0, 0, 1080, 300, BG, 0, z=0),
        _grad("ao-a-scrim",460, 0, 200, 300, _FADE_L, 90, z=4),
        _circle("ao-a-c",  -60, -60, 300, "rgba(0,0,0,0.10)", z=1),
        _txt("ao-a-title", "offer_title",    PAD, 24,  460, 80, 40, "Syne",       700, "rgba(255,255,255,0.75)", "left", 1.0, 0.5, z=5),
        _txt("ao-a-price", "price",          PAD, 96,  440, 130, 110,"Bebas Neue", 900, WHT, "left", 0.84, -3, z=6),
        _txt("ao-a-badge", "discount_label", PAD, 240,  360, 58, 32, "Bebas Neue", 800, BLK, "left", 1.0, 2, z=5),
    ],

    # B: Black bg, brand-color price badge, product image right
    [
        _rect("ao-b-bg",   0, 0, 1080, 300, BLK, 0, z=0),
        _grad("ao-b-scrim",460, 0, 200, 300, _FADE_L, 90, z=4),
        _txt("ao-b-title", "offer_title",    PAD, 22,  480, 70, 32, "Syne",      600, "rgba(255,255,255,0.60)", "left", 1.0, 1, z=5),
        _txt("ao-b-price", "price",          PAD, 90,  440, 130, 108,"Bebas Neue",900, WHT, "left", 0.84, -3, z=6),
        _rect("ao-b-bdg",  PAD, 230, 300, 60, BG, 6, z=5, shadowBlur=18, shadowX=0, shadowY=5, shadowColor="rgba(0,0,0,0.55)"),
        _txt("ao-b-badge", "discount_label", PAD+14, 244, 272, 36, 26, "Bebas Neue", 800, WHT, "center", 1.0, 1, z=6),
    ],

    # C: Brand-color band across middle, price in white inside
    [
        _rect("ao-c-bg",   0, 0, 1080, 300, DK, 0, z=0),
        _rect("ao-c-band", 0, 68, 1080, 150, BG, 0, z=2),
        _txt("ao-c-title", "offer_title",    PAD, 18,  580, 50, 26, "Syne",      500, "rgba(255,255,255,0.55)", "left", 1.0, 1.5, z=5),
        _txt("ao-c-price", "price",          PAD, 76,  500, 130, 110,"Bebas Neue",900, WHT, "left", 0.84, -3, z=6),
        _txt("ao-c-badge", "discount_label", PAD, 232,  400, 52, 26, "Syne", 700, "rgba(255,255,255,0.75)", "left", 1.2, 2, z=5),
    ],

    # D: Full brand-color, price enormous, no product image — pure type ad
    [
        _rect("ao-d-bg",   0, 0, 1080, 300, BG, 0, z=0),
        _circle("ao-d-c1", 800, -80, 400, "rgba(0,0,0,0.10)", z=1),
        _circle("ao-d-c2", -80, 160, 260, "rgba(255,255,255,0.06)", z=1),
        _txt("ao-d-title", "offer_title",    PAD, 18,  700, 46, 26, "Syne",       600, "rgba(255,255,255,0.65)", "left", 1.0, 2, z=5),
        _txt("ao-d-price", "price",          PAD, 60,  700, 148, 118,"Bebas Neue", 900, WHT, "left", 0.82, -4, z=6),
        _txt("ao-d-badge", "discount_label", PAD, 224,  460, 60,  34, "Bebas Neue",800, BLK, "left", 1.0, 2, z=5),
        _rect("ao-d-bdg-bg",PAD-8,220, 300, 66, "rgba(255,255,255,0.85)", 6, z=4),
    ],
]


# ── FEATURE LIST — 340px ──────────────────────────────────────────────────────

ADVERTISE_FEATURES: List[List[Dict]] = [

    # A: Brand-color bg, bold headline, 4 features as punchy white lines
    [
        _rect("afl-a-bg", 0, 0, 1080, 340, BG, 0, z=0),
        _circle("afl-a-c",900, -60, 400, "rgba(0,0,0,0.10)", z=1),
        _txt("afl-a-head","headline", PAD, 22, 860, 78, 58, "Bebas Neue", 900, WHT, "left", 0.92, -1, z=5),
        _rect("afl-a-rule",PAD, 108, 80, 5, "rgba(255,255,255,0.40)", 999, z=4),
        *[s for i in range(1,5) for s in [
            _circle(f"afl-a-m{i}", PAD+4, 130+(i-1)*54+20, 10, WHT, z=4, op=0.55),
            _txt(f"afl-a-f{i}", f"feature_{i}", PAD+26, 130+(i-1)*54, 840, 50, 26, "Syne", 500,
                 "rgba(255,255,255,0.85)", "left", 1.2, 0, z=5),
        ]],
    ],

    # B: Black bg, brand-color headline accent, 2-column punchy features
    [
        _rect("afl-b-bg", 0, 0, 1080, 340, BLK, 0, z=0),
        _rect("afl-b-top",0, 0, 1080, 5, BG, 0, z=2),
        _txt("afl-b-head","headline", PAD, 22, 860, 78, 54, "Bebas Neue", 900, WHT, "left", 0.92, -1, z=5),
        *[s for i,(x,y) in enumerate([(PAD,116),(560,116),(PAD,204),(560,204)],1) for s in [
            _rect(f"afl-b-a{i}", x, y+12, 6, 28, BG, 999, z=4),
            _txt(f"afl-b-f{i}", f"feature_{i}", x+18, y, 448, 50, 24, "Syne", 500,
                 "rgba(255,255,255,0.80)", "left", 1.2, 0, z=5),
        ]],
    ],

    # C: Brand-color left stripe + dark bg, numbered Bebas lines
    [
        _rect("afl-c-bg",  0, 0, 1080, 340, DK, 0, z=0),
        _rect("afl-c-bar", 0, 0, 10, 340, BG, 0, z=2),
        _txt("afl-c-head","headline", PAD+18, 18, 860, 76, 52, "Bebas Neue", 900, WHT, "left", 0.93, -1, z=5),
        *[s for i in range(1,5) for s in [
            _txt(f"afl-c-n{i}", "deco_icon", PAD+18, 102+(i-1)*58, 52, 50, 36, "Bebas Neue", 900, A, "left", 1.0, 0, z=4),
            _txt(f"afl-c-f{i}", f"feature_{i}", PAD+78, 102+(i-1)*58, 800, 50, 24, "Syne", 500,
                 "rgba(255,255,255,0.80)", "left", 1.2, 0, z=5),
            _rect(f"afl-c-sep{i}", PAD+78, 148+(i-1)*58, 800, 1, "rgba(255,255,255,0.07)", 0, z=3),
        ]],
    ],

    # D: Brand-color right panel with product, features on dark left
    [
        _rect("afl-d-dark", 0, 0, 560, 340, DK, 0, z=0),
        _rect("afl-d-col",  560, 0, 520, 340, BG, 0, z=0),
        _txt("afl-d-head","headline", PAD, 20, 510, 70, 46, "Bebas Neue", 900, WHT, "left", 0.93, -1, z=5),
        *[_txt(f"afl-d-f{i}", f"feature_{i}", PAD, 98+(i-1)*58, 510, 50, 22, "Syne", 500,
               "rgba(255,255,255,0.75)", "left", 1.2, 0, z=5) for i in range(1,5)],
    ],
]


# ── HEADLINE — 260px ──────────────────────────────────────────────────────────

ADVERTISE_HEADLINE: List[List[Dict]] = [

    # A: Brand-color bg, hook enormous white, nothing else
    [
        _rect("ahl-a-bg",  0, 0, 1080, 260, BG, 0, z=0),
        _circle("ahl-a-c", 900, -80, 360, "rgba(0,0,0,0.12)", z=1),
        _txt("ahl-a-hook", "hook",       PAD, PAD, 880, 165, 92, "Bebas Neue", 900, WHT, "left", 0.88, -2, z=5),
        _txt("ahl-a-sub",  "subheading", PAD, 218, 700,  52, 24, "Syne",       400, "rgba(255,255,255,0.65)", "left", 1.3, 0, z=5),
    ],

    # B: Black bg, brand-color left bar, hook right-shifted
    [
        _rect("ahl-b-bg",  0, 0, 1080, 260, BLK, 0, z=0),
        _rect("ahl-b-bar", 0, 0, 10, 260, BG, 0, z=2),
        _txt("ahl-b-hook", "hook",       PAD+18, PAD, 860, 162, 90, "Bebas Neue", 900, WHT, "left", 0.88, -2, z=5),
        _txt("ahl-b-sub",  "subheading", PAD+18, 216, 700,  52, 24, "Syne",       400, "rgba(255,255,255,0.55)", "left", 1.3, 0, z=5),
    ],

    # C: Brand-color bottom half, dark top, hook spans both zones
    [
        _rect("ahl-c-dark",0, 0, 1080, 150, DK, 0, z=0),
        _rect("ahl-c-col", 0, 150, 1080, 110, BG, 0, z=0),
        _txt("ahl-c-hook", "hook",       PAD, 28, 880, 168, 92, "Bebas Neue", 900, WHT, "left", 0.88, -2, z=5),
        _txt("ahl-c-sub",  "subheading", PAD, 204, 700,  52, 22, "Syne",       400, "rgba(255,255,255,0.65)", "left", 1.3, 0, z=5),
    ],

    # D: Brand-color right strip, dark left, hook dominant left — minimal poster
    [
        _rect("ahl-d-dark",0, 0, 940, 260, DK, 0, z=0),
        _rect("ahl-d-col", 940, 0, 140, 260, BG, 0, z=0),
        _txt("ahl-d-hook", "hook",       PAD, PAD, 860, 162, 90, "Bebas Neue", 900, WHT, "left", 0.88, -2, z=5),
        _txt("ahl-d-sub",  "subheading", PAD, 220, 700,  50, 22, "Syne",       400, "rgba(255,255,255,0.52)", "left", 1.3, 0, z=5),
    ],
]


# ── SPONSOR BAR — 170px ───────────────────────────────────────────────────────

ADVERTISE_SPONSOR: List[List[Dict]] = [

    # A: Brand-color bg, proof label small, logos
    [
        _rect("asp-a-bg",   0, 0, 1080, 170, BG, 0, z=0),
        _txt("asp-a-label","proof", PAD, 14, 968, 28, 16, "Syne", 500, "rgba(255,255,255,0.45)", "center", 1.0, 3, z=5),
        *[_img(f"asp-a-l{i}", f"sponsor_{i}", PAD+(i-1)*236, 48, 196, 92, fit="contain", r=0, z=4) for i in range(1,5)],
    ],

    # B: Black, brand-color rule, logos
    [
        _rect("asp-b-bg",   0, 0, 1080, 170, BLK, 0, z=0),
        _rect("asp-b-rule", PAD, 14, 968, 4, BG, 999, z=3),
        _txt("asp-b-label","proof", PAD, 28, 968, 26, 15, "Syne", 400, "rgba(255,255,255,0.28)", "center", 1.0, 3, z=5),
        *[_img(f"asp-b-l{i}", f"sponsor_{i}", PAD+(i-1)*236, 56, 196, 90, fit="contain", r=0, z=4) for i in range(1,5)],
    ],

    # C: Dark, pill containers, brand-color outline
    [
        _rect("asp-c-bg", 0, 0, 1080, 170, DK, 0, z=0),
        _txt("asp-c-label","proof", PAD, 10, 968, 26, 14, "Syne", 400, "rgba(255,255,255,0.25)", "center", 1.0, 3, z=5),
        *[s for i in range(1,5) for s in [
            _rect(f"asp-c-box{i}", PAD+(i-1)*240, 44, 202, 96, "rgba(255,255,255,0.03)", 10, z=3, borderColor=BG, borderWidth=1),
            _img(f"asp-c-l{i}", f"sponsor_{i}", PAD+(i-1)*240+10, 54, 182, 76, fit="contain", r=0, z=4),
        ]],
    ],

    # D: Brand-color + dark split, logos centred
    [
        _rect("asp-d-col", 0, 0, 1080, 60, BG, 0, z=0),
        _rect("asp-d-dark",0, 60, 1080, 110, DK, 0, z=0),
        _txt("asp-d-label","proof", PAD, 18, 968, 28, 14, "Syne", 600, WHT, "center", 1.0, 3, z=5),
        *[_img(f"asp-d-l{i}", f"sponsor_{i}", PAD+(i-1)*236, 68, 196, 88, fit="contain", r=0, z=4) for i in range(1,5)],
    ],
]


# ══════════════════════════════════════════════════════════════════════════════
#  STORY TONE
#  Rule: image top, editorial dark panel below. Text is readable body size.
#  Hierarchy over impact. Serif-weight Syne. Never overlap text on image.
#  Reference: gallery editorial card (Image 2).
# ══════════════════════════════════════════════════════════════════════════════

# ── HERO — 430px ──────────────────────────────────────────────────────────────

STORY_HERO: List[List[Dict]] = [

    # A: Portrait top 260px, dark panel below — exact Image 2 rhythm
    [
        _rect("sh-a-panel", 0, 260, 1080, 170, DK, 0, z=3),
        _txt("sh-a-hook", "hook",       PAD, 272, 880, 118, 50, "Syne", 700, WHT, "left", 1.08, -0.5, z=5),
        _txt("sh-a-sub",  "subheading", PAD, 396, 760,  50, 20, "Syne", 400, "rgba(255,255,255,0.58)", "left", 1.5, 0, z=5),
    ],

    # B: Image top 300px, editorial strip below, accent rule
    [
        _rect("sh-b-strip", 0, 300, 1080, 130, DK, 0, z=3),
        _rect("sh-b-rule",  PAD, 300, 72, 3, A, 0, z=4),
        _txt("sh-b-hook", "hook",       PAD, 312, 800, 88, 42, "Syne", 700, WHT, "left", 1.10, -0.5, z=5),
        _txt("sh-b-sub",  "subheading", PAD, 406, 680,  38, 18, "Syne", 400, "rgba(255,255,255,0.55)", "left", 1.5, 0, z=5),
    ],

    # C: Full image, semi-transparent panel anchored bottom
    [
        _rect("sh-c-panel", 0, 300, 1080, 130, "rgba(4,6,10,0.93)", 0, z=4),
        _txt("sh-c-hook", "hook",       PAD, 310, 800, 88, 42, "Syne", 700, WHT, "left", 1.1, -0.5, z=5),
        _txt("sh-c-sub",  "subheading", PAD, 404, 680,  38, 18, "Syne", 400, "rgba(255,255,255,0.58)", "left", 1.5, 0, z=5),
    ],

    # D: Side split — image left 50%, editorial right panel
    [
        _grad("sh-d-scrim", 380, 0, 200, 430,
              [{"stop":0,"color":"rgba(5,7,11,0)"},{"stop":1,"color":"rgba(5,7,11,1)"}], 90, z=3),
        _rect("sh-d-panel", 540, 0, 540, 430, DK, 0, z=3),
        _txt("sh-d-hook", "hook",       558, 58,  460, 240, 48, "Syne", 700, WHT, "left", 1.08, -0.5, z=5),
        _txt("sh-d-sub",  "subheading", 558, 308, 460,  80, 18, "Syne", 400, "rgba(255,255,255,0.58)", "left", 1.5, 0, z=5),
        _txt("sh-d-cta",  "cta_text",   558, 396, 300,  38, 16, "Syne", 600, A, "left", 1.0, 1, z=5),
    ],
]


# ── CTA — 160px ───────────────────────────────────────────────────────────────

STORY_CTA: List[List[Dict]] = [

    # A: Editorial CTA — underlined link style, no heavy button
    [
        _rect("sc-a-bg",   0, 0, 1080, 160, DK, 0, z=0),
        _rect("sc-a-line", PAD, 0, 968, 1, "rgba(255,255,255,0.12)", 0, z=2),
        _txt("sc-a-cta",   "cta_text", PAD, 42, 600, 60, 30, "Syne", 600, WHT, "left", 1.0, -0.5, z=5),
        _rect("sc-a-ul",   PAD, 104, 380, 2, A, 0, z=4),
        _txt("sc-a-proof", "proof",    PAD, 112, 700, 38, 15, "Syne", 400, "rgba(255,255,255,0.44)", "left", 1.5, 0, z=5),
    ],

    # B: Outlined accent button
    [
        _rect("sc-b-bg",   0, 0, 1080, 160, DK, 0, z=0),
        _rect("sc-b-btn",  PAD, 32, 360, 66, "transparent", 6, z=4, borderColor=A, borderWidth=2),
        _txt("sc-b-cta",   "cta_text", PAD+16, 48, 328, 36, 24, "Syne", 600, A, "center", 1.0, -0.5, z=5),
        _txt("sc-b-proof", "proof",    PAD+4, 108, 700, 38, 15, "Syne", 400, "rgba(255,255,255,0.44)", "left", 1.5, 0, z=5),
    ],

    # C: Accent top rule, text only
    [
        _rect("sc-c-bg",   0, 0, 1080, 160, DK, 0, z=0),
        _rect("sc-c-rule", 0, 0, 1080, 3, A, 0, z=2),
        _txt("sc-c-cta",   "cta_text", PAD, 44, 750, 62, 34, "Syne", 700, WHT, "left", 1.0, -0.5, z=5),
        _txt("sc-c-proof", "proof",    820, 54, 204, 44, 20, "Syne", 500, A, "right", 1.0, 1, z=5),
    ],

    # D: Image strip behind, soft scrim
    [
        _rect("sc-d-ov", 0, 0, 1080, 160, "rgba(4,6,10,0.82)", 0, z=3),
        _txt("sc-d-cta",   "cta_text", PAD, 40, 600, 62, 30, "Syne", 600, WHT, "left", 1.0, -0.5, z=5),
        _txt("sc-d-proof", "proof",    PAD, 108, 700, 38, 15, "Syne", 400, "rgba(255,255,255,0.48)", "left", 1.5, 0, z=5),
    ],
]


# ── REVIEW — 260px ────────────────────────────────────────────────────────────

STORY_REVIEW: List[List[Dict]] = [

    # A: Serif italic quote, left accent rule
    [
        _rect("sr-a-bg",   0, 0, 1080, 260, DK, 0, z=0),
        _rect("sr-a-rule", PAD-6, PAD-6, 5, 138, A, 2, z=3),
        _txt("sr-a-text",   "review_text",   PAD+10, PAD, 860, 138, 26,
             "Georgia,serif", 400, "rgba(255,255,255,0.88)", "left", 1.62, 0, z=5, fontStyle="italic"),
        _txt("sr-a-author", "review_author", PAD,    192, 500,  44, 18, "Syne", 600, WHT, "left", 1.0, 2, z=5),
        _txt("sr-a-rating", "review_rating", PAD,    230, 200,  30, 18, "Syne", 400, A, "left", 1.0, 2, z=5),
    ],

    # B: Image top strip, quote below
    [
        _rect("sr-b-panel", 0, 100, 1080, 160, DK, 0, z=3),
        _txt("sr-b-text",   "review_text",   PAD, 108, 880, 110, 24,
             "Georgia,serif", 400, "rgba(255,255,255,0.88)", "left", 1.55, 0, z=5, fontStyle="italic"),
        _txt("sr-b-author", "review_author", PAD, 226, 400,  34, 16, "Syne", 600, WHT, "left", 1.0, 1, z=5),
        _txt("sr-b-rating", "review_rating", 500, 228, 300,  32, 16, "Syne", 400, A, "right", 1.0, 2, z=5),
    ],

    # C: Card with accent border
    [
        _rect("sr-c-bg",   0, 0, 1080, 260, DK, 0, z=0),
        _rect("sr-c-card", PAD-16, 16, 1048, 228, "rgba(255,255,255,0.03)", 14, z=3, borderColor=A, borderWidth=1),
        _txt("sr-c-text",   "review_text",   PAD+6, 36, 860, 132, 24,
             "Georgia,serif", 400, "rgba(255,255,255,0.88)", "left", 1.58, 0, z=5, fontStyle="italic"),
        _txt("sr-c-author", "review_author", PAD+6, 178, 440,  44, 16, "Syne", 600, WHT, "left", 1.0, 1, z=5),
        _txt("sr-c-rating", "review_rating", PAD+6, 218, 200,  34, 16, "Syne", 400, A, "left", 1.0, 2, z=5),
    ],

    # D: Thin rule, quote, author right
    [
        _rect("sr-d-bg",   0, 0, 1080, 260, DK, 0, z=0),
        _txt("sr-d-text",  "review_text",   PAD, PAD, 880, 138, 26,
             "Georgia,serif", 400, "rgba(255,255,255,0.88)", "left", 1.58, 0, z=5, fontStyle="italic"),
        _rect("sr-d-rule", PAD, 188, 900, 2, A, 999, z=3),
        _txt("sr-d-author","review_author", PAD, 196, 500,  44, 16, "Syne", 600, WHT, "left", 1.0, 1, z=5),
        _txt("sr-d-rating","review_rating", 700, 200, 324,  44, 16, "Syne", 400, A, "right", 1.0, 2, z=5),
    ],
]


# ── FOOTER — 190px ────────────────────────────────────────────────────────────

STORY_FOOTER: List[List[Dict]] = [

    # A: Editorial footer — logo left, company, web + social right
    [
        _rect("sft-a-bg",   0, 0, 1080, 190, DK, 0, z=0),
        _rect("sft-a-rule", PAD, 0, 968, 1, "rgba(255,255,255,0.13)", 0, z=2),
        _txt("sft-a-co",    "companyName",      PAD+142, 34, 360, 42, 24, "Syne", 700, WHT, "left", 1.0, -0.5, z=5),
        _txt("sft-a-row1",  "contact_row1",     PAD,     108, 560, 34, 14, "Syne", 400, "rgba(255,255,255,0.50)", "left", 1.5, 0, z=5),
        _txt("sft-a-web",   "business_website", 620,     108, 404, 34, 14, "Syne", 500, A, "right", 1.0, 0, z=5),
        _txt("sft-a-soc",   "social_handle",    620,      34, 404, 42, 18, "Syne", 600, "rgba(255,255,255,0.58)", "right", 1.0, 0.5, z=5),
    ],

    # B: Accent top stripe, centred logo, two-row contact
    [
        _rect("sft-b-bg",    0, 0, 1080, 190, DK, 0, z=0),
        _grad_rect("sft-b-stripe", 0, 0, 1080, 4,
                   [{"stop":0,"color":A},{"stop":0.5,"color":"rgba(255,255,255,0.4)"},{"stop":1,"color":A}], 90, z=1),
        _txt("sft-b-row1",   "contact_row1",     PAD, 98,  640, 32, 14, "Syne", 400, "rgba(255,255,255,0.55)", "left", 1.5, 0, z=5),
        _txt("sft-b-row2",   "contact_row2",     PAD, 132, 640, 28, 12, "Syne", 400, "rgba(255,255,255,0.34)", "left", 1.5, 0, z=5),
        _txt("sft-b-web",    "business_website", 700, 106, 324, 30, 14, "Syne", 600, A, "right", 1.0, 0, z=5),
    ],

    # C: Left accent line, stacked contact
    [
        _rect("sft-c-bg",     0, 0, 1080, 190, DK, 0, z=0),
        _rect("sft-c-accent", 0, 0, 4,   190, A,  0, z=1),
        _txt("sft-c-co",     "companyName",      PAD+14,  82, 380, 42, 22, "Syne", 700, WHT, "left", 1.0, -0.5, z=5),
        _txt("sft-c-row1",   "contact_row1",     PAD+14, 132, 560, 32, 13, "Syne", 400, "rgba(255,255,255,0.50)", "left", 1.5, 0, z=5),
        _txt("sft-c-web",    "business_website", 640,     38, 384, 34, 16, "Syne", 600, A, "right", 1.0, 0, z=5),
        _txt("sft-c-soc",    "social_handle",    640,     82, 384, 42, 18, "Syne", 500, "rgba(255,255,255,0.55)", "right", 1.0, 0.5, z=5),
    ],

    # D: Dark panel, top accent + mid divider, date/category tag style
    [
        _rect("sft-d-bg",     0,  0, 1080, 190, "#030507", 0, z=0),
        _rect("sft-d-top",    0,  0, 1080,   2, A, 0, z=1),
        _rect("sft-d-mid",    0, 94, 1080,   1, "rgba(255,255,255,0.07)", 0, z=1),
        _txt("sft-d-row1",   "contact_row1",     PAD,  16, 640, 32, 16, "Syne", 400, "rgba(255,255,255,0.64)", "left", 1.5, 0, z=5),
        _txt("sft-d-row2",   "contact_row2",     PAD,  52, 640, 28, 12, "Syne", 400, "rgba(255,255,255,0.36)", "left", 1.5, 0, z=5),
        _txt("sft-d-web",    "business_website", PAD, 106, 500, 32, 14, "Syne", 600, A, "left", 1.0, 0, z=5),
        _txt("sft-d-co",     "companyName",      710,  96, 314, 42, 20, "Syne", 700, "rgba(255,255,255,0.54)", "right", 1.0, -0.5, z=5),
    ],
]


# ── OFFER / PRICE — 300px ─────────────────────────────────────────────────────

STORY_OFFER: List[List[Dict]] = [

    # A: Image top, editorial price/offer below
    [
        _rect("sof-a-panel", 0, 158, 1080, 142, DK, 0, z=3),
        _rect("sof-a-rule",  PAD, 158, 72, 3, A, 0, z=4),
        _txt("sof-a-title", "offer_title",    PAD, 168, 640, 74, 36, "Syne",       700, WHT, "left", 1.0, -0.5, z=5),
        _txt("sof-a-price", "price",          680, 158, 344, 96, 70, "Bebas Neue", 900, A,   "right", 0.88, -1, z=5),
        _txt("sof-a-label", "discount_label", PAD, 250, 400, 44, 16, "Syne",       500, "rgba(255,255,255,0.55)", "left", 1.0, 1.5, z=5),
    ],

    # B: Two-column — text left, price right
    [
        _rect("sof-b-bg",  0, 0, 1080, 300, DK, 0, z=0),
        _txt("sof-b-title","offer_title",       PAD, 34,  500, 108, 40, "Syne",       700, WHT, "left", 1.05, -0.5, z=5),
        _txt("sof-b-desc", "offer_description", PAD, 150, 500, 78, 18, "Syne",       400, "rgba(255,255,255,0.58)", "left", 1.5, 0, z=5),
        _txt("sof-b-label","discount_label",    PAD, 238, 380, 44, 16, "Syne",       600, A, "left", 1.0, 1.5, z=5),
        _rect("sof-b-div", 558, 34, 1, 240, "rgba(255,255,255,0.10)", 0, z=3),
        _txt("sof-b-price","price",             578, 58,  440, 130, 86, "Bebas Neue", 900, A, "center", 0.87, -2, z=5),
        _txt("sof-b-comp", "compare_at_price",  578, 194, 440, 60,  22, "Syne",       400, "rgba(255,255,255,0.40)", "center", 1.2, 0, z=5),
    ],

    # C: Card style on dark
    [
        _rect("sof-c-bg",   0, 0, 1080, 300, DK, 0, z=0),
        _rect("sof-c-card", PAD-16, 16, 1048, 268, "rgba(255,255,255,0.04)", 14, z=3, borderColor="rgba(255,255,255,0.10)", borderWidth=1),
        _txt("sof-c-title", "offer_title",       PAD+6, 32, 700, 88, 38, "Syne", 700, WHT, "left", 1.05, -0.5, z=5),
        _txt("sof-c-desc",  "offer_description", PAD+6, 128, 700, 74, 17, "Syne", 400, "rgba(255,255,255,0.56)", "left", 1.5, 0, z=5),
        _txt("sof-c-price", "price",             800, 32, 232, 110, 74, "Bebas Neue", 900, A, "right", 0.87, -2, z=5),
        _txt("sof-c-label", "discount_label",    PAD+6, 212, 380, 44, 15, "Syne", 500, A, "left", 1.0, 1.5, z=5),
    ],

    # D: Metadata row — small label, big title, price inline
    [
        _rect("sof-d-bg",   0, 0, 1080, 300, DK, 0, z=0),
        _txt("sof-d-label", "discount_label",    PAD,  20, 500, 38, 12, "Syne", 600, A, "left", 1.0, 2.5, z=5),
        _rect("sof-d-rule", PAD, 60, 968, 1, "rgba(255,255,255,0.10)", 0, z=3),
        _txt("sof-d-title", "offer_title",       PAD,  68, 700, 98, 42, "Syne", 700, WHT, "left", 1.05, -0.5, z=5),
        _txt("sof-d-price", "price",             PAD, 174, 420, 106, 82, "Bebas Neue", 900, A, "left", 0.86, -2, z=5),
        _txt("sof-d-comp",  "compare_at_price",  488, 206, 300, 62, 22, "Syne", 400, "rgba(255,255,255,0.38)", "left", 1.2, 0, z=5),
    ],
]


# ── FEATURE LIST — 340px ──────────────────────────────────────────────────────

STORY_FEATURES: List[List[Dict]] = [

    # A: Image top, readable features below
    [
        _rect("sfl-a-panel",0, 98, 1080, 242, DK, 0, z=3),
        _txt("sfl-a-head",  "headline", PAD, 106, 860, 64, 32, "Syne", 700, WHT, "left", 1.05, -0.5, z=5),
        *[_txt(f"sfl-a-f{i}", f"feature_{i}", PAD, 178+(i-1)*42, 860, 40, 16, "Syne", 400,
               "rgba(255,255,255,0.68)", "left", 1.4, 0, z=5) for i in range(1,5)],
    ],

    # B: Thin dividers, serif-weight header
    [
        _rect("sfl-b-bg",  0, 0, 1080, 340, DK, 0, z=0),
        _txt("sfl-b-head", "headline", PAD, 26, 860, 64, 34, "Syne", 700, WHT, "left", 1.05, -0.5, z=5),
        _rect("sfl-b-rule",PAD, 98, 968, 1, "rgba(255,255,255,0.12)", 0, z=3),
        *[s for i in range(1,5) for s in [
            _txt(f"sfl-b-f{i}", f"feature_{i}", PAD, 108+(i-1)*56, 840, 46, 18, "Syne", 400,
                 "rgba(255,255,255,0.68)", "left", 1.4, 0, z=5),
            _rect(f"sfl-b-d{i}", PAD, 150+(i-1)*56, 968, 1, "rgba(255,255,255,0.07)", 0, z=3),
        ]],
    ],

    # C: Two-column accent-dot grid
    [
        _rect("sfl-c-bg",  0, 0, 1080, 340, DK, 0, z=0),
        _txt("sfl-c-head", "headline", PAD, 22, 860, 64, 32, "Syne", 700, WHT, "left", 1.05, -0.5, z=5),
        *[s for i,(x,y,w) in enumerate([(PAD,98,460),(PAD+514,98,460),(PAD,190,460),(PAD+514,190,460)],1) for s in [
            _rect(f"sfl-c-d{i}", x, y, 3, 34, A, 0, z=4),
            _txt(f"sfl-c-f{i}", f"feature_{i}", x+16, y, w-16, 42, 17, "Syne", 400,
                 "rgba(255,255,255,0.68)", "left", 1.35, 0, z=5),
        ]],
        _rect("sfl-c-mv", PAD+506, 94, 1, 200, "rgba(255,255,255,0.08)", 0, z=3),
    ],

    # D: Numbered editorial
    [
        _rect("sfl-d-bg",  0, 0, 1080, 340, DK, 0, z=0),
        _txt("sfl-d-head", "headline", PAD, 20, 860, 64, 32, "Syne", 700, WHT, "left", 1.05, -0.5, z=5),
        *[s for i in range(1,5) for s in [
            _txt(f"sfl-d-n{i}", "deco_icon", PAD, 94+(i-1)*58, 44, 44, 26, "Syne", 700, A, "left", 1.0, 0, z=4),
            _txt(f"sfl-d-f{i}", f"feature_{i}", PAD+54, 94+(i-1)*58, 820, 46, 17, "Syne", 400,
                 "rgba(255,255,255,0.68)", "left", 1.4, 0, z=5),
            _rect(f"sfl-d-r{i}", PAD+54, 136+(i-1)*58, 820, 1, "rgba(255,255,255,0.07)", 0, z=3),
        ]],
    ],
]


# ── HEADLINE — 260px ──────────────────────────────────────────────────────────

STORY_HEADLINE: List[List[Dict]] = [

    # A: Image top, editorial headline below — Image 2 structure
    [
        _rect("sthl-a-panel",0, 138, 1080, 122, DK, 0, z=3),
        _txt("sthl-a-hook",  "hook",       PAD, 146, 880, 88, 36, "Syne", 700, WHT, "left", 1.08, -0.5, z=5),
        _txt("sthl-a-sub",   "subheading", PAD, 240, 760, 50, 16, "Syne", 400, "rgba(255,255,255,0.54)", "left", 1.5, 0, z=5),
    ],

    # B: Hook large, proof tag, accent rule
    [
        _rect("sthl-b-bg",   0, 0, 1080, 260, DK, 0, z=0),
        _txt("sthl-b-hook",  "hook",       PAD, 34,  880, 138, 50, "Syne", 700, WHT, "left", 1.08, -0.5, z=5),
        _rect("sthl-b-rule", PAD, 180, 72, 2, A, 0, z=3),
        _txt("sthl-b-sub",   "subheading", PAD, 188, 760, 54, 16, "Syne", 400, "rgba(255,255,255,0.54)", "left", 1.5, 0, z=5),
        _txt("sthl-b-proof", "proof",      PAD, 216, 500, 32, 12, "Syne", 500, A, "left", 1.0, 1.5, z=5),
    ],

    # C: Left image, right editorial
    [
        _grad("sthl-c-scrim",376, 0, 182, 260,
              [{"stop":0,"color":"rgba(5,7,11,0)"},{"stop":1,"color":"rgba(5,7,11,1)"}], 90, z=3),
        _rect("sthl-c-panel",518, 0, 562, 260, DK, 0, z=3),
        _txt("sthl-c-hook",  "hook",       536, 34,  502, 138, 38, "Syne", 700, WHT, "left", 1.08, -0.5, z=5),
        _txt("sthl-c-sub",   "subheading", 536, 180, 502, 54, 15, "Syne", 400, "rgba(255,255,255,0.54)", "left", 1.5, 0, z=5),
    ],

    # D: Proof tag + rule + hook + subheading
    [
        _rect("sthl-d-bg",   0, 0, 1080, 260, DK, 0, z=0),
        _txt("sthl-d-proof", "proof",      PAD, 26, 500, 32, 12, "Syne", 500, A, "left", 1.0, 2, z=5),
        _rect("sthl-d-rule", PAD, 60, 968, 1, "rgba(255,255,255,0.12)", 0, z=3),
        _txt("sthl-d-hook",  "hook",       PAD, 72,  880, 128, 44, "Syne", 700, WHT, "left", 1.08, -0.5, z=5),
        _txt("sthl-d-sub",   "subheading", PAD, 208, 760, 50, 15, "Syne", 400, "rgba(255,255,255,0.54)", "left", 1.5, 0, z=5),
    ],
]


# ── SPONSOR — 170px ───────────────────────────────────────────────────────────

STORY_SPONSOR: List[List[Dict]] = [

    # A: Thin top rule, small label, logos
    [
        _rect("ssp-a-bg",   0, 0, 1080, 170, DK, 0, z=0),
        _rect("ssp-a-rule", PAD, 12, 968, 1, "rgba(255,255,255,0.14)", 0, z=2),
        _txt("ssp-a-label", "proof", PAD, 20, 968, 26, 12, "Syne", 400, "rgba(255,255,255,0.30)", "center", 1.0, 2.5, z=5),
        *[_img(f"ssp-a-l{i}", f"sponsor_{i}", PAD+(i-1)*236, 54, 196, 90, fit="contain", r=0, z=4) for i in range(1,5)],
    ],

    # B: Card-wrapped logos
    [
        _rect("ssp-b-bg",    0, 0, 1080, 170, DK, 0, z=0),
        _txt("ssp-b-label",  "proof", PAD, 8, 968, 24, 11, "Syne", 400, "rgba(255,255,255,0.27)", "center", 1.0, 2.5, z=5),
        *[s for i in range(1,5) for s in [
            _rect(f"ssp-b-card{i}", PAD+(i-1)*238, 38, 202, 102, "rgba(255,255,255,0.04)", 10, z=3, borderColor="rgba(255,255,255,0.09)", borderWidth=1),
            _img(f"ssp-b-l{i}", f"sponsor_{i}", PAD+(i-1)*238+10, 48, 182, 82, fit="contain", r=0, z=4),
        ]],
    ],

    # C: Accent top bar, logos
    [
        _rect("ssp-c-bg",   0, 0, 1080, 170, DK, 0, z=0),
        _rect("ssp-c-bar",  0, 0, 1080, 3, A, 0, z=2),
        _txt("ssp-c-label", "proof", PAD, 8, 968, 24, 11, "Syne", 400, "rgba(255,255,255,0.27)", "center", 1.0, 2.5, z=5),
        *[_img(f"ssp-c-l{i}", f"sponsor_{i}", PAD+(i-1)*236, 44, 196, 92, fit="contain", r=0, z=4) for i in range(1,5)],
    ],

    # D: Gradient overlay behind logos
    [
        _rect("ssp-d-ov", 0, 0, 1080, 170, "rgba(4,6,10,0.84)", 0, z=3),
        _txt("ssp-d-label","proof", PAD, 6, 968, 24, 11, "Syne", 400, "rgba(255,255,255,0.34)", "center", 1.0, 2.5, z=5),
        *[_img(f"ssp-d-l{i}", f"sponsor_{i}", PAD+(i-1)*236, 40, 196, 96, fit="contain", r=0, z=4) for i in range(1,5)],
    ],
]


# ══════════════════════════════════════════════════════════════════════════════
#  SEGMENT FIELDS — per tone (CRITICAL: fewer fields for advertise)
# ══════════════════════════════════════════════════════════════════════════════

TONE_SEGMENT_FIELDS: Dict[str, Dict[str, List[str]]] = {
    "advertise": {
        # Advertise: max 2-3 text shapes. Hook + badge only. No body copy.
        "hero_image":   ["hook", "cta_text", "discount_label"],
        "offer_block":  ["offer_title", "price", "discount_label"],
        "price_block":  ["price", "discount_label"],
        "feature_list": ["headline", "feature_1", "feature_2", "feature_3", "feature_4"],
        "review_block": ["review_text", "review_author", "review_rating"],
        "sponsor_bar":  ["proof"],
        "cta_button":   ["cta_text", "proof"],
        "footer":       ["companyName", "business_website", "social_handle"],
        "headline":     ["hook", "subheading"],
        "product_card": ["offer_title", "price", "discount_label"],
    },
    "story": {
        # Story: full editorial — headline + subheading + body + metadata
        "hero_image":   ["hook", "subheading", "cta_text"],
        "offer_block":  ["offer_title", "offer_description", "discount_label", "price", "compare_at_price"],
        "price_block":  ["price", "compare_at_price", "discount_label"],
        "feature_list": ["headline", "feature_1", "feature_2", "feature_3", "feature_4"],
        "review_block": ["review_text", "review_author", "review_rating"],
        "sponsor_bar":  ["proof"],
        "cta_button":   ["cta_text", "proof"],
        "footer":       ["companyName", "contact_row1", "contact_row2", "business_website", "social_handle"],
        "headline":     ["hook", "subheading", "proof"],
        "product_card": ["offer_title", "offer_description", "price", "compare_at_price", "discount_label"],
    },
}

# Default fallback fields
_DEFAULT_FIELDS: Dict[str, List[str]] = {
    "hero_image":   ["hook", "cta_text", "discount_label"],
    "offer_block":  ["offer_title", "price", "discount_label"],
    "price_block":  ["price", "discount_label"],
    "feature_list": ["headline", "feature_1", "feature_2", "feature_3", "feature_4"],
    "review_block": ["review_text", "review_author", "review_rating"],
    "sponsor_bar":  ["proof"],
    "cta_button":   ["cta_text", "proof"],
    "footer":       ["companyName", "business_website", "social_handle"],
    "headline":     ["hook", "subheading"],
    "product_card": ["offer_title", "price", "discount_label"],
}


# ══════════════════════════════════════════════════════════════════════════════
#  REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

_TONE_BLUEPRINTS: Dict[str, Dict[str, Any]] = {
    "advertise": {
        "hero_image":   {"height": 430, "variants": ADVERTISE_HERO},
        "cta_button":   {"height": 160, "variants": ADVERTISE_CTA},
        "review_block": {"height": 260, "variants": ADVERTISE_REVIEW},
        "footer":       {"height": 190, "variants": ADVERTISE_FOOTER},
        "offer_block":  {"height": 300, "variants": ADVERTISE_OFFER},
        "price_block":  {"height": 300, "variants": ADVERTISE_OFFER},
        "feature_list": {"height": 340, "variants": ADVERTISE_FEATURES},
        "headline":     {"height": 260, "variants": ADVERTISE_HEADLINE},
        "sponsor_bar":  {"height": 170, "variants": ADVERTISE_SPONSOR},
    },
    "story": {
        "hero_image":   {"height": 430, "variants": STORY_HERO},
        "cta_button":   {"height": 160, "variants": STORY_CTA},
        "review_block": {"height": 260, "variants": STORY_REVIEW},
        "footer":       {"height": 190, "variants": STORY_FOOTER},
        "offer_block":  {"height": 300, "variants": STORY_OFFER},
        "price_block":  {"height": 300, "variants": STORY_OFFER},
        "feature_list": {"height": 340, "variants": STORY_FEATURES},
        "headline":     {"height": 260, "variants": STORY_HEADLINE},
        "sponsor_bar":  {"height": 170, "variants": STORY_SPONSOR},
    },
}

_DEFAULT_TONE = "advertise"


def get_blueprint(
    segment_type: str,
    brand_seed:   int = 0,
    tone_name:    str = _DEFAULT_TONE,
) -> Optional[Dict[str, Any]]:
    tone_key = (tone_name or _DEFAULT_TONE).lower().strip()
    tone_map = _TONE_BLUEPRINTS.get(tone_key) or _TONE_BLUEPRINTS[_DEFAULT_TONE]
    entry    = tone_map.get(segment_type) or _TONE_BLUEPRINTS[_DEFAULT_TONE].get(segment_type)

    if not entry:
        return None

    variants = entry["variants"]
    height   = entry["height"]
    variant  = variants[brand_seed % len(variants)]

    return {
        "segment_type":   segment_type,
        "segment_height": height,
        "shapes":         variant,
        "variant_index":  brand_seed % len(variants),
        "total_variants": len(variants),
        "tone":           tone_key,
    }


def get_tone_fields(segment_type: str, tone_name: str = _DEFAULT_TONE) -> List[str]:
    tone_key = (tone_name or _DEFAULT_TONE).lower().strip()
    fields = TONE_SEGMENT_FIELDS.get(tone_key, _DEFAULT_FIELDS)
    return fields.get(segment_type, _DEFAULT_FIELDS.get(segment_type, ["hook"]))


def list_tones() -> List[str]:
    return list(_TONE_BLUEPRINTS.keys())


def list_segment_types(tone_name: str = _DEFAULT_TONE) -> List[str]:
    tone_key = (tone_name or _DEFAULT_TONE).lower().strip()
    return list((_TONE_BLUEPRINTS.get(tone_key) or _TONE_BLUEPRINTS[_DEFAULT_TONE]).keys())