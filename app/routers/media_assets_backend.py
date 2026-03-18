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
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session

from app.database import Base, get_db

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


# ── Router ────────────────────────────────────────────────────────────────────
# redirect_slashes=False: accepts both /media-assets and /media-assets/
# without issuing a 307 that can silently convert POST→GET.
# Route paths use "" (not "/") so FastAPI doesn't register a second
# conflicting route at the prefix root.

router = APIRouter(redirect_slashes=False)


@router.get("", response_model=List[MediaAssetOut])
def list_media_assets(
    type:     Optional[str] = Query(None),
    brand_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = select(MediaAsset).order_by(MediaAsset.created_at.desc())
    if type:     q = q.where(MediaAsset.type == type)
    if brand_id: q = q.where(MediaAsset.brand_id == brand_id)
    return [MediaAssetOut.from_orm(r) for r in db.execute(q).scalars().all()]


@router.post("", response_model=MediaAssetOut, status_code=201)
def create_media_asset(payload: CreateMediaAssetPayload, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    asset = MediaAsset(
        id=_uuid.uuid4(), url=payload.url, filename=payload.filename, type=payload.type,
        brand_id=payload.brand_id or None,
        brand_name=payload.brand_name, tags=payload.tags,
        size_bytes=payload.size_bytes, mime_type=payload.mime_type,
        width=payload.width, height=payload.height,
        created_at=now, updated_at=now,
    )
    db.add(asset); db.commit(); db.refresh(asset)
    return MediaAssetOut.from_orm(asset)


@router.patch("/{asset_id}", response_model=MediaAssetOut)
def update_media_asset(asset_id: str, payload: UpdateMediaAssetPayload, db: Session = Depends(get_db)):
    asset = db.execute(
        select(MediaAsset).where(MediaAsset.id == _uuid.UUID(asset_id))
    ).scalars().first()
    if not asset: raise HTTPException(404, "Asset not found")
    if payload.brand_id is not None:
        asset.brand_id   = payload.brand_id or None
        asset.brand_name = payload.brand_name
    if payload.tags is not None:
        asset.tags = payload.tags
    asset.updated_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(asset)
    return MediaAssetOut.from_orm(asset)


@router.delete("/{asset_id}", status_code=204)
def delete_media_asset(asset_id: str, db: Session = Depends(get_db)):
    asset = db.execute(
        select(MediaAsset).where(MediaAsset.id == _uuid.UUID(asset_id))
    ).scalars().first()
    if not asset: raise HTTPException(404, "Asset not found")
    db.delete(asset); db.commit()


# ── Helper used by other services ────────────────────────────────────────────

def get_assets_for_brand(
    db: Session,
    brand_id: str,
    asset_type: str = "video",
    portrait_only: bool = True,
    limit: int = 20,
) -> list[MediaAsset]:
    """Fetch assets for a brand. Used by generate_monthly_drafts and Studio."""
    assets = list(db.execute(
        select(MediaAsset)
        .where(MediaAsset.brand_id == brand_id)
        .where(MediaAsset.type == asset_type)
    ).scalars().all())
    if portrait_only and assets:
        portrait = [a for a in assets if a.height and a.width and a.height > a.width]
        if portrait:
            assets = portrait
    random.shuffle(assets)
    return assets[:limit]