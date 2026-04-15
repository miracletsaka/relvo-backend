from __future__ import annotations

import uuid as _uuid
import random
import json
from datetime import datetime, timezone
from typing import List, Optional

from app.models.media_asset import MediaAsset
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.org import get_current_org
from app.models.organisation import Organisation


# ── Schemas ───────────────────────────────────────────────────────────────────

class MediaAssetOut(BaseModel):
    id:             str
    url:            str
    filename:       str
    type:           str
    brand_id:       Optional[str]   = None
    brand_name:     Optional[str]   = None
    tags:           List[str]       = []
    size_bytes:     Optional[int]   = None
    mime_type:      Optional[str]   = None
    width:          Optional[int]   = None
    height:         Optional[int]   = None
    price:          Optional[float] = None   # product price — optional
    price_currency: Optional[str]   = "USD"
    created_at:     str
    updated_at:     str

    @classmethod
    def from_orm(cls, obj: MediaAsset) -> "MediaAssetOut":
        return cls(
            id=str(obj.id), url=obj.url, filename=obj.filename, type=obj.type,
            brand_id=str(obj.brand_id) if obj.brand_id else None,
            brand_name=obj.brand_name, tags=obj.tags or [],
            size_bytes=obj.size_bytes, mime_type=obj.mime_type,
            width=obj.width, height=obj.height,
            price=float(obj.price) if obj.price is not None else None,
            price_currency=getattr(obj, "price_currency", "USD") or "USD",
            created_at=obj.created_at.isoformat(),
            updated_at=obj.updated_at.isoformat(),
        )

    @classmethod
    def from_row(cls, row: dict) -> "MediaAssetOut":
        price_raw = row.get("price")
        return cls(
            id=str(row["id"]), url=row["url"], filename=row["filename"], type=row["type"],
            brand_id=str(row["brand_id"]) if row.get("brand_id") else None,
            brand_name=row.get("brand_name"), tags=row.get("tags") or [],
            size_bytes=row.get("size_bytes"), mime_type=row.get("mime_type"),
            width=row.get("width"), height=row.get("height"),
            price=float(price_raw) if price_raw is not None else None,
            price_currency=row.get("price_currency") or "USD",
            created_at=row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
            updated_at=row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else str(row["updated_at"]),
        )


class CreateMediaAssetPayload(BaseModel):
    url:            str
    filename:       str
    type:           str
    brand_id:       Optional[str]   = None
    brand_name:     Optional[str]   = None
    tags:           List[str]       = []
    size_bytes:     Optional[int]   = None
    mime_type:      Optional[str]   = None
    width:          Optional[int]   = None
    height:         Optional[int]   = None
    price:          Optional[float] = None
    price_currency: Optional[str]   = "USD"


class UpdateMediaAssetPayload(BaseModel):
    brand_id:       Optional[str]       = None
    brand_name:     Optional[str]       = None
    tags:           Optional[List[str]] = None
    price:          Optional[float]     = None   # set to 0.0 to clear price
    price_currency: Optional[str]       = None


router = APIRouter(prefix="/media-assets", tags=["media-assets"])


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[MediaAssetOut])
def list_media_assets(
    type:     Optional[str] = Query(None),
    brand_id: Optional[str] = Query(None),
    org = Depends(get_current_org),          # ← NEW
    db: Session = Depends(get_db),
):
    where_clauses = ["org_id = :org_id"]     # ← NEW — always scope to org
    params: dict  = {"org_id": str(org.id)}

    if type:
        where_clauses.append("type = :type")
        params["type"] = type
    if brand_id:
        where_clauses.append("brand_id::text = :brand_id")
        params["brand_id"] = brand_id

    where_sql = "WHERE " + " AND ".join(where_clauses)
    rows = db.execute(
        text(f"SELECT * FROM media_assets {where_sql} ORDER BY created_at DESC"),
        params,
    ).mappings().all()
    return [MediaAssetOut.from_row(dict(r)) for r in rows]


@router.post("", response_model=MediaAssetOut, status_code=201)
def create_media_asset(
    payload: CreateMediaAssetPayload,
    org = Depends(get_current_org),          # ← NEW
    db: Session = Depends(get_db),
):
    now      = datetime.now(timezone.utc)
    asset_id = _uuid.uuid4()
    tags_json = json.dumps(payload.tags or [])

    db.execute(text("""
        INSERT INTO media_assets
            (id, url, filename, type, brand_id, brand_name, tags,
             size_bytes, mime_type, width, height, org_id,
             price, price_currency, created_at, updated_at)
        VALUES
            (:id, :url, :filename, :type, :brand_id, :brand_name, CAST(:tags AS json),
             :size_bytes, :mime_type, :width, :height, :org_id,
             :price, :price_currency, :created_at, :updated_at)
    """), {
        "id":             str(asset_id),
        "url":            payload.url,
        "filename":       payload.filename,
        "type":           payload.type,
        "brand_id":       payload.brand_id or None,
        "brand_name":     payload.brand_name,
        "tags":           tags_json,
        "size_bytes":     payload.size_bytes,
        "mime_type":      payload.mime_type,
        "width":          payload.width,
        "height":         payload.height,
        "org_id":         str(org.id),
        "price":          payload.price,
        "price_currency": payload.price_currency or "USD",
        "created_at":     now,
        "updated_at":     now,
    })
    db.commit()

    row = db.execute(
        text("SELECT * FROM media_assets WHERE id = :id"),
        {"id": str(asset_id)},
    ).mappings().first()

    if not row:
        raise HTTPException(500, "Asset was inserted but could not be retrieved")

    return MediaAssetOut.from_row(dict(row))


@router.patch("/{asset_id}", response_model=MediaAssetOut)
def update_media_asset(
    asset_id: str,
    payload: UpdateMediaAssetPayload,
    org = Depends(get_current_org),          # ← NEW
    db: Session = Depends(get_db),
):
    set_clauses = ["updated_at = :updated_at"]
    params: dict = {
        "asset_id": asset_id,
        "org_id":   str(org.id),             # ← NEW
        "updated_at": datetime.now(timezone.utc),
    }

    if payload.brand_id is not None:
        set_clauses.append("brand_id = :brand_id")
        set_clauses.append("brand_name = :brand_name")
        params["brand_id"]   = payload.brand_id or None
        params["brand_name"] = payload.brand_name

    if payload.tags is not None:
        set_clauses.append("tags = CAST(:tags AS json)")
        params["tags"] = json.dumps(payload.tags)

    if payload.price is not None:
        set_clauses.append("price = :price")
        params["price"] = payload.price if payload.price > 0 else None

    if payload.price_currency is not None:
        set_clauses.append("price_currency = :price_currency")
        params["price_currency"] = payload.price_currency.upper()[:3]

    db.execute(
        text(f"""
            UPDATE media_assets
            SET {', '.join(set_clauses)}
            WHERE id::text = :asset_id
              AND org_id   = :org_id
        """),                                # ← NEW — scoped to org
        params,
    )
    db.commit()

    row = db.execute(
        text("SELECT * FROM media_assets WHERE id::text = :asset_id AND org_id = :org_id"),
        {"asset_id": asset_id, "org_id": str(org.id)},
    ).mappings().first()

    if not row:
        raise HTTPException(404, "Asset not found")

    return MediaAssetOut.from_row(dict(row))


@router.delete("/{asset_id}", status_code=204)
def delete_media_asset(
    asset_id: str,
    org = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    result = db.execute(
        text("DELETE FROM media_assets WHERE id::text = :asset_id AND org_id = :org_id"),
        {"asset_id": asset_id, "org_id": str(org.id)},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Asset not found")


# ── Dedicated price endpoint ───────────────────────────────────────────────────

class UpdatePricePayload(BaseModel):
    price:          Optional[float] = None   # None or 0 = clear price
    price_currency: Optional[str]   = "USD"


@router.patch("/{asset_id}/price", response_model=MediaAssetOut)
def update_asset_price(
    asset_id: str,
    payload:  UpdatePricePayload,
    org = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    """
    Set or clear the price on a media asset.
    Send price=null or price=0 to remove the price.
    """
    price_value = None if (payload.price is None or payload.price <= 0) else payload.price
    currency    = (payload.price_currency or "USD").upper()[:3]

    result = db.execute(
        text("""
            UPDATE media_assets
            SET price = :price, price_currency = :currency, updated_at = NOW()
            WHERE id::text = :asset_id AND org_id = :org_id
        """),
        {"price": price_value, "currency": currency, "asset_id": asset_id, "org_id": str(org.id)},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "Asset not found")

    row = db.execute(
        text("SELECT * FROM media_assets WHERE id::text = :asset_id AND org_id = :org_id"),
        {"asset_id": asset_id, "org_id": str(org.id)},
    ).mappings().first()

    return MediaAssetOut.from_row(dict(row))


# ── Helper used by other services (unchanged) ─────────────────────────────────

def get_assets_for_brand(
    db: Session,
    brand_id: str,
    asset_type: str = "video",
    portrait_only: bool = True,
    limit: int = 20,
) -> list:
    rows = db.execute(
        text("""
            SELECT * FROM media_assets
            WHERE brand_id::text = :brand_id
              AND type = :type
        """),
        {"brand_id": brand_id, "type": asset_type},
    ).mappings().all()

    assets = [dict(r) for r in rows]

    if portrait_only and assets:
        portrait = [a for a in assets if a.get("height") and a.get("width") and a["height"] > a["width"]]
        if portrait:
            assets = portrait

    random.shuffle(assets)
    return assets[:limit]