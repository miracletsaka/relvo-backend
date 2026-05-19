# backend/app/services/blueprints/shared.py

from typing import Dict, List, Optional

PAD = 56
A = "__BRAND_ACCENT__"
DK = "#05070b"
BLK = "#000000"
WHT = "#ffffff"

def txt(id_, df, x, y, w, h, fs, ff, fw, tc, ta="left", lh=1.0, ls=0, z=5, **kw):
    return {
        "id": id_,
        "type": "text",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "dataField": df,
        "text": "",
        "fontSize": fs,
        "fontFamily": ff,
        "fontWeight": fw,
        "textColor": tc,
        "textAlign": ta,
        "lineHeight": lh,
        "letterSpacing": ls,
        "padding": 8,
        "zIndex": z,
        "opacity": 1,
        "backgroundColor": "transparent",
        "borderColor": "transparent",
        "borderWidth": 0,
        "shadowBlur": 0,
        "shadowX": 0,
        "shadowY": 0,
        "shadowColor": "#000000",
        **kw,
    }

def rect(id_, x, y, w, h, bg, r=0, z=3, op=1, **kw):
    return {
        "id": id_,
        "type": "rounded-rect",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "backgroundColor": bg,
        "borderRadius": r,
        "zIndex": z,
        "opacity": op,
        "borderColor": "transparent",
        "borderWidth": 0,
        "shadowBlur": 0,
        "shadowX": 0,
        "shadowY": 0,
        "shadowColor": "#000000",
        **kw,
    }

def circle(id_, x, y, size, bg, z=2, op=1.0):
    return {
        "id": id_,
        "type": "circle",
        "x": x,
        "y": y,
        "width": size,
        "height": size,
        "backgroundColor": bg,
        "zIndex": z,
        "opacity": op,
        "borderColor": "transparent",
        "borderWidth": 0,
        "shadowBlur": 0,
        "shadowX": 0,
        "shadowY": 0,
        "shadowColor": "#000000",
    }

def img(id_, sk, x, y, w, h, fit="cover", r=0, z=1, op=1.0, rotate=0):
    return {
        "id": id_,
        "type": "image",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "slotKey": sk,
        "slotLabel": sk.replace("_", " ").title(),
        "slotType": "logo" if sk == "logo" else "image",
        "slotRole": "logo" if sk == "logo" else "hero",
        "fit": fit,
        "radius": r,
        "rotation": rotate,
        "slotVisibleWhenEmpty": sk == "logo",
        "src": None,
        "zIndex": z,
        "opacity": op,
        "backgroundColor": "transparent",
        "borderColor": "transparent",
        "borderWidth": 0,
        "shadowBlur": 0,
        "shadowX": 0,
        "shadowY": 0,
        "shadowColor": "#000000",
    }

def grad(id_, x, y, w, h, stops, angle=180, z=2, op=1):
    return {
        "id": id_,
        "type": "gradient-overlay",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "gradientColors": stops,
        "gradientAngle": angle,
        "backgroundColor": "transparent",
        "borderWidth": 0,
        "zIndex": z,
        "opacity": op,
    }

def package_blueprint(segment_type: str, height: int, variants: List[List[Dict]], index: int):
    variant = variants[index % len(variants)]
    return {
        "segment_type": segment_type,
        "segment_height": height,
        "variant_index": index % len(variants),
        "shapes": variant,
    }
