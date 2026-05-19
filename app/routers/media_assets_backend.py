from __future__ import annotations

import uuid as _uuid
import random
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from app.models.media_asset import MediaAsset
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.org import get_current_org


class MediaAssetOut(BaseModel):
    id: str
    url: str
    filename: str
    type: str
    brand_id: Optional[str] = None
    brand_name: Optional[str] = None
    tags: List[str] = []
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    price_currency: Optional[str] = "MWK"
    compare_at_price: Optional[float] = None
    discount_label: Optional[str] = None
    offer_title: Optional[str] = None
    offer_description: Optional[str] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    availability: Optional[str] = "available"
    product_category: Optional[str] = None
    service_area: Optional[str] = None
    features: List[str] = []
    metadata: Dict[str, Any] = {}

    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: dict) -> "MediaAssetOut":
        return cls(
            id=str(row["id"]),
            url=row["url"],
            filename=row["filename"],
            type=row["type"],
            brand_id=str(row["brand_id"]) if row.get("brand_id") else None,
            brand_name=row.get("brand_name"),
            tags=row.get("tags") or [],
            size_bytes=row.get("size_bytes"),
            mime_type=row.get("mime_type"),
            width=row.get("width"),
            height=row.get("height"),

            title=row.get("title"),
            description=row.get("description"),
            price=float(row["price"]) if row.get("price") is not None else None,
            price_currency=row.get("price_currency") or "MWK",
            compare_at_price=float(row["compare_at_price"]) if row.get("compare_at_price") is not None else None,
            discount_label=row.get("discount_label"),
            offer_title=row.get("offer_title"),
            offer_description=row.get("offer_description"),
            cta_text=row.get("cta_text"),
            cta_url=row.get("cta_url"),
            availability=row.get("availability") or "available",
            product_category=row.get("product_category"),
            service_area=row.get("service_area"),
            features=row.get("features") or [],
            metadata=row.get("metadata") or {},

            created_at=row["created_at"].isoformat()
            if hasattr(row["created_at"], "isoformat")
            else str(row["created_at"]),
            updated_at=row["updated_at"].isoformat()
            if hasattr(row["updated_at"], "isoformat")
            else str(row["updated_at"]),
        )


class CreateMediaAssetPayload(BaseModel):
    url: str
    filename: str
    type: str
    brand_id: Optional[str] = None
    brand_name: Optional[str] = None
    tags: List[str] = []
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    price_currency: Optional[str] = "MWK"
    compare_at_price: Optional[float] = None
    discount_label: Optional[str] = None
    offer_title: Optional[str] = None
    offer_description: Optional[str] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    availability: Optional[str] = "available"
    product_category: Optional[str] = None
    service_area: Optional[str] = None
    features: List[str] = []
    metadata: Dict[str, Any] = {}


class UpdateMediaAssetPayload(BaseModel):
    brand_id: Optional[str] = None
    brand_name: Optional[str] = None
    tags: Optional[List[str]] = None

    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    price_currency: Optional[str] = None
    compare_at_price: Optional[float] = None
    discount_label: Optional[str] = None
    offer_title: Optional[str] = None
    offer_description: Optional[str] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    availability: Optional[str] = None
    product_category: Optional[str] = None
    service_area: Optional[str] = None
    features: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


router = APIRouter(prefix="/media-assets", tags=["media-assets"])


def clean_currency(value: Optional[str]) -> str:
    return (value or "MWK").upper()[:10]


def positive_or_none(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return value if value > 0 else None


@router.get("", response_model=List[MediaAssetOut])
def list_media_assets(
    type: Optional[str] = Query(None),
    brand_id: Optional[str] = Query(None),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
):
    where_clauses = ["org_id = :org_id"]
    params: dict = {"org_id": str(org.id)}

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
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    asset_id = _uuid.uuid4()

    db.execute(
        text("""
            INSERT INTO media_assets
                (
                    id, url, filename, type, brand_id, brand_name, tags,
                    size_bytes, mime_type, width, height, org_id,
                    title, description, price, price_currency, compare_at_price,
                    discount_label, offer_title, offer_description, cta_text, cta_url,
                    availability, product_category, service_area, features, metadata,
                    created_at, updated_at
                )
            VALUES
                (
                    :id, :url, :filename, :type, :brand_id, :brand_name, CAST(:tags AS json),
                    :size_bytes, :mime_type, :width, :height, :org_id,
                    :title, :description, :price, :price_currency, :compare_at_price,
                    :discount_label, :offer_title, :offer_description, :cta_text, :cta_url,
                    :availability, :product_category, :service_area, CAST(:features AS jsonb), CAST(:metadata AS jsonb),
                    :created_at, :updated_at
                )
        """),
        {
            "id": str(asset_id),
            "url": payload.url,
            "filename": payload.filename,
            "type": payload.type,
            "brand_id": payload.brand_id or None,
            "brand_name": payload.brand_name,
            "tags": json.dumps(payload.tags or []),
            "size_bytes": payload.size_bytes,
            "mime_type": payload.mime_type,
            "width": payload.width,
            "height": payload.height,
            "org_id": str(org.id),

            "title": payload.title,
            "description": payload.description,
            "price": positive_or_none(payload.price),
            "price_currency": clean_currency(payload.price_currency),
            "compare_at_price": positive_or_none(payload.compare_at_price),
            "discount_label": payload.discount_label,
            "offer_title": payload.offer_title,
            "offer_description": payload.offer_description,
            "cta_text": payload.cta_text,
            "cta_url": payload.cta_url,
            "availability": payload.availability or "available",
            "product_category": payload.product_category,
            "service_area": payload.service_area,
            "features": json.dumps(payload.features or []),
            "metadata": json.dumps(payload.metadata or {}),

            "created_at": now,
            "updated_at": now,
        },
    )
    db.commit()

    row = db.execute(
        text("SELECT * FROM media_assets WHERE id = :id AND org_id = :org_id"),
        {"id": str(asset_id), "org_id": str(org.id)},
    ).mappings().first()

    if not row:
        raise HTTPException(500, "Asset was inserted but could not be retrieved")

    return MediaAssetOut.from_row(dict(row))


@router.patch("/{asset_id}", response_model=MediaAssetOut)
def update_media_asset(
    asset_id: str,
    payload: UpdateMediaAssetPayload,
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
):
    set_clauses = ["updated_at = :updated_at"]
    params: dict = {
        "asset_id": asset_id,
        "org_id": str(org.id),
        "updated_at": datetime.now(timezone.utc),
    }

    if payload.brand_id is not None:
        set_clauses.append("brand_id = :brand_id")
        set_clauses.append("brand_name = :brand_name")
        params["brand_id"] = payload.brand_id or None
        params["brand_name"] = payload.brand_name

    if payload.tags is not None:
        set_clauses.append("tags = CAST(:tags AS json)")
        params["tags"] = json.dumps(payload.tags)

    if payload.price is not None:
        set_clauses.append("price = :price")
        params["price"] = positive_or_none(payload.price)

    if payload.price_currency is not None:
        set_clauses.append("price_currency = :price_currency")
        params["price_currency"] = clean_currency(payload.price_currency)

    if payload.compare_at_price is not None:
        set_clauses.append("compare_at_price = :compare_at_price")
        params["compare_at_price"] = positive_or_none(payload.compare_at_price)

    for field in [
        "title",
        "description",
        "discount_label",
        "offer_title",
        "offer_description",
        "cta_text",
        "cta_url",
        "availability",
        "product_category",
        "service_area",
    ]:
        value = getattr(payload, field)
        if value is not None:
            set_clauses.append(f"{field} = :{field}")
            params[field] = value

    if payload.features is not None:
        set_clauses.append("features = CAST(:features AS jsonb)")
        params["features"] = json.dumps(payload.features)

    if payload.metadata is not None:
        set_clauses.append("metadata = CAST(:metadata AS jsonb)")
        params["metadata"] = json.dumps(payload.metadata)

    db.execute(
        text(f"""
            UPDATE media_assets
            SET {', '.join(set_clauses)}
            WHERE id::text = :asset_id
              AND org_id = :org_id
        """),
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
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
):
    result = db.execute(
        text("DELETE FROM media_assets WHERE id::text = :asset_id AND org_id = :org_id"),
        {"asset_id": asset_id, "org_id": str(org.id)},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "Asset not found")


class UpdatePricePayload(BaseModel):
    price: Optional[float] = None
    price_currency: Optional[str] = "MWK"
    compare_at_price: Optional[float] = None
    discount_label: Optional[str] = None
    offer_title: Optional[str] = None
    offer_description: Optional[str] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None


@router.patch("/{asset_id}/price", response_model=MediaAssetOut)
def update_asset_price(
    asset_id: str,
    payload: UpdatePricePayload,
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
):
    result = db.execute(
        text("""
            UPDATE media_assets
            SET
                price = :price,
                price_currency = :currency,
                compare_at_price = :compare_at_price,
                discount_label = :discount_label,
                offer_title = :offer_title,
                offer_description = :offer_description,
                cta_text = :cta_text,
                cta_url = :cta_url,
                updated_at = NOW()
            WHERE id::text = :asset_id
              AND org_id = :org_id
        """),
        {
            "price": positive_or_none(payload.price),
            "currency": clean_currency(payload.price_currency),
            "compare_at_price": positive_or_none(payload.compare_at_price),
            "discount_label": payload.discount_label,
            "offer_title": payload.offer_title,
            "offer_description": payload.offer_description,
            "cta_text": payload.cta_text,
            "cta_url": payload.cta_url,
            "asset_id": asset_id,
            "org_id": str(org.id),
        },
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(404, "Asset not found")

    row = db.execute(
        text("SELECT * FROM media_assets WHERE id::text = :asset_id AND org_id = :org_id"),
        {"asset_id": asset_id, "org_id": str(org.id)},
    ).mappings().first()

    return MediaAssetOut.from_row(dict(row))


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
        portrait = [
            a for a in assets
            if a.get("height") and a.get("width") and a["height"] > a["width"]
        ]
        if portrait:
            assets = portrait

    random.shuffle(assets)
    return assets[:limit]