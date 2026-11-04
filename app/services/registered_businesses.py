"""
Finds businesses REGISTERED in this app (organisations + org_business_info) that have a phone number.
Matching is deliberately loose, so a demo with few registered businesses still works.
"""
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

STOP = {"business", "businesses", "company", "companies", "service", "services", "shop", "shops",
        "store", "stores", "local", "small", "clinic", "clinics", "that", "need", "with", "from"}


def _words(value: str) -> list[str]:
    words = [w.lower() for w in re.findall(r"[A-Za-z]{4,}", value or "")]
    return [w[:-1] if w.endswith("s") else w for w in words if w not in STOP][:3]


def search_registered(db: Session, caller_org_id, business_type: str, city: str,
                      count: int, include_self: bool) -> list[dict]:
    params: dict = {"org": caller_org_id, "self": include_self, "n": max(1, min(count, 10))}
    where = [
        "o.is_active = true",
        "COALESCE(NULLIF(b.phone_primary, ''), NULLIF(b.phone_secondary, ''), NULLIF(b.whatsapp, '')) IS NOT NULL",
        "(:self OR o.id <> :org)",
    ]

    type_words = _words(business_type)
    if type_words:
        ors = []
        for i, w in enumerate(type_words):
            params[f"t{i}"] = f"%{w}%"
            ors.append(f"(b.business_type ILIKE :t{i} OR o.name ILIKE :t{i} "
                       f"OR b.tagline ILIKE :t{i} OR b.description ILIKE :t{i})")
        where.append("(" + " OR ".join(ors) + ")")

    city = (city or "").strip()
    if city:
        params["city"] = f"%{city}%"
        where.append("(b.city ILIKE :city OR b.state_province ILIKE :city OR b.country ILIKE :city)")

    rows = db.execute(
        text(
            f"""
            SELECT o.id::text AS org_id, o.name,
                   COALESCE(NULLIF(b.phone_primary, ''), NULLIF(b.phone_secondary, ''), NULLIF(b.whatsapp, '')) AS phone,
                   b.address, b.city, b.state_province, b.website, b.business_type
            FROM organisations o
            JOIN org_business_info b ON b.org_id = o.id
            WHERE {' AND '.join(where)}
            ORDER BY o.created_at DESC
            LIMIT :n
            """
        ),
        params,
    ).mappings().all()

    return [
        {
            "org_id": r["org_id"],
            "name": r["name"],
            "phone": (r["phone"] or "").strip(),
            "address": ", ".join(x for x in [r["address"], r["city"], r["state_province"]] if x),
            "website": r["website"] or "",
            "business_type": r["business_type"] or "",
        }
        for r in rows
    ]
