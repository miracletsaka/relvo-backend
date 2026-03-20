from __future__ import annotations

"""
app/routers/media_assets.py
────────────────────────────
Mount in main.py:
    from app.routers import media_assets
    app.include_router(media_assets.router, prefix="/media-assets", tags=["media-assets"])
"""

import uuid as _uuid
import random
from datetime import datetime, timezone
from typing import List, Optional

from app.models.media_asset import MediaAsset
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import get_db


# ── Schemas ───────────────────────────────────────────────────────────────────

class MediaAssetOut(BaseModel):
    id:         str
    url:        str
    filename:   str
    type:       str
    brand_id:   Optional[str] = None
    brand_name: Optional[str] = None
    tags:       List[str]     = []
    size_bytes: Optional[int] = None
    mime_type:  Optional[str] = None
    width:      Optional[int] = None
    height:     Optional[int] = None
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(cls, obj: MediaAsset) -> "MediaAssetOut":
        return cls(
            id=str(obj.id), url=obj.url, filename=obj.filename, type=obj.type,
            brand_id=str(obj.brand_id) if obj.brand_id else None,
            brand_name=obj.brand_name, tags=obj.tags or [],
            size_bytes=obj.size_bytes, mime_type=obj.mime_type,
            width=obj.width, height=obj.height,
            created_at=obj.created_at.isoformat(),
            updated_at=obj.updated_at.isoformat(),
        )

    @classmethod
    def from_row(cls, row: dict) -> "MediaAssetOut":
        """Build from a raw SQL row dict (used when ORM cast would fail)."""
        return cls(
            id=str(row["id"]), url=row["url"], filename=row["filename"], type=row["type"],
            brand_id=str(row["brand_id"]) if row.get("brand_id") else None,
            brand_name=row.get("brand_name"), tags=row.get("tags") or [],
            size_bytes=row.get("size_bytes"), mime_type=row.get("mime_type"),
            width=row.get("width"), height=row.get("height"),
            created_at=row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
            updated_at=row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else str(row["updated_at"]),
        )


class CreateMediaAssetPayload(BaseModel):
    url:        str
    filename:   str
    type:       str
    brand_id:   Optional[str] = None
    brand_name: Optional[str] = None
    tags:       List[str]     = []
    size_bytes: Optional[int] = None
    mime_type:  Optional[str] = None
    width:      Optional[int] = None
    height:     Optional[int] = None


class UpdateMediaAssetPayload(BaseModel):
    brand_id:   Optional[str]       = None
    brand_name: Optional[str]       = None
    tags:       Optional[List[str]] = None


router = APIRouter(prefix="/media-assets", tags=["media-assets"])


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[MediaAssetOut])
def list_media_assets(
    type:     Optional[str] = Query(None),
    brand_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    # Use raw SQL so brand_id is compared as text — avoids UUID cast errors
    # when brand_id column is UUID type but values are string slugs.
    where_clauses = []
    params: dict = {}
    if type:
        where_clauses.append("type = :type")
        params["type"] = type
    if brand_id:
        where_clauses.append("brand_id::text = :brand_id")
        params["brand_id"] = brand_id

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    rows = db.execute(
        text(f"SELECT * FROM media_assets {where_sql} ORDER BY created_at DESC"),
        params,
    ).mappings().all()
    return [MediaAssetOut.from_row(dict(r)) for r in rows]


@router.post("", response_model=MediaAssetOut, status_code=201)
def create_media_asset(payload: CreateMediaAssetPayload, db: Session = Depends(get_db)):
    """
    INSERT using raw SQL so brand_id is stored as plain text rather than
    being cast to UUID by SQLAlchemy. The DB column is UUID but brand IDs
    are string slugs (e.g. 'neuroflow-software') — the cast fails at the
    ORM layer. Inserting brand_id as text bypasses this.
    """
    now       = datetime.now(timezone.utc)
    asset_id  = _uuid.uuid4()
    import json

    # Serialize tags to JSON string in Python — avoids :param::json syntax
    # which conflicts with psycopg2's %(name)s parameter style
    tags_json = json.dumps(payload.tags or [])

    db.execute(text("""
        INSERT INTO media_assets
            (id, url, filename, type, brand_id, brand_name, tags,
             size_bytes, mime_type, width, height, created_at, updated_at)
        VALUES
            (:id, :url, :filename, :type, :brand_id, :brand_name, CAST(:tags AS json),
             :size_bytes, :mime_type, :width, :height, :created_at, :updated_at)
    """), {
        "id":         str(asset_id),
        "url":        payload.url,
        "filename":   payload.filename,
        "type":       payload.type,
        "brand_id":   payload.brand_id or None,
        "brand_name": payload.brand_name,
        "tags":       tags_json,
        "size_bytes": payload.size_bytes,
        "mime_type":  payload.mime_type,
        "width":      payload.width,
        "height":     payload.height,
        "created_at": now,
        "updated_at": now,
    })
    db.commit()

    # Fetch back the row we just inserted using text() to avoid UUID cast
    row = db.execute(
        text("SELECT * FROM media_assets WHERE id = :id"),
        {"id": str(asset_id)},
    ).mappings().first()

    if not row:
        raise HTTPException(500, "Asset was inserted but could not be retrieved")

    return MediaAssetOut.from_row(dict(row))


@router.patch("/{asset_id}", response_model=MediaAssetOut)
def update_media_asset(asset_id: str, payload: UpdateMediaAssetPayload, db: Session = Depends(get_db)):
    import json
    set_clauses = ["updated_at = :updated_at"]
    params: dict = {"asset_id": asset_id, "updated_at": datetime.now(timezone.utc)}

    if payload.brand_id is not None:
        set_clauses.append("brand_id = :brand_id")
        set_clauses.append("brand_name = :brand_name")
        params["brand_id"]   = payload.brand_id or None
        params["brand_name"] = payload.brand_name

    if payload.tags is not None:
        set_clauses.append("tags = CAST(:tags AS json)")
        params["tags"] = json.dumps(payload.tags)

    db.execute(
        text(f"UPDATE media_assets SET {', '.join(set_clauses)} WHERE id::text = :asset_id"),
        params,
    )
    db.commit()

    row = db.execute(
        text("SELECT * FROM media_assets WHERE id::text = :asset_id"),
        {"asset_id": asset_id},
    ).mappings().first()

    if not row:
        raise HTTPException(404, "Asset not found")

    return MediaAssetOut.from_row(dict(row))


@router.delete("/{asset_id}", status_code=204)
def delete_media_asset(asset_id: str, db: Session = Depends(get_db)):
    result = db.execute(
        text("DELETE FROM media_assets WHERE id::text = :asset_id"),
        {"asset_id": asset_id},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Asset not found")


# ── Helper used by other services ────────────────────────────────────────────

def get_assets_for_brand(
    db: Session,
    brand_id: str,
    asset_type: str = "video",
    portrait_only: bool = True,
    limit: int = 20,
) -> list:
    """Fetch assets for a brand. Uses text comparison to avoid UUID cast errors."""
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