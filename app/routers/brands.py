from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, text
from app.database import get_db
from app.models.brand import Brand
from app.schemas.brand import BrandCreate, BrandUpdate, BrandOut
from app.models.brand_profile import BrandProfile
from app.models.media_asset import MediaAsset
from app.models.topic_chat import TopicChat
from app.models.content_draft import ContentDraft

router = APIRouter(prefix="/brands", tags=["brands"])

@router.get("", response_model=list[BrandOut])
def list_brands(db: Session = Depends(get_db), active_only: bool = True):
    q = select(Brand)
    if active_only:
        q = q.where(Brand.is_active == True)  # noqa
    return db.execute(q).scalars().all()

@router.post("", response_model=BrandOut)
def create_brand(payload: BrandCreate, db: Session = Depends(get_db)):
    existing = db.get(Brand, payload.id)
    if existing:
        raise HTTPException(status_code=400, detail="Brand id already exists")

    brand = Brand(
        id=payload.id.strip(),
        display_name=payload.display_name.strip(),
        is_active=payload.is_active,
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand

@router.patch("/{brand_id}", response_model=BrandOut)
def update_brand(brand_id: str, payload: BrandUpdate, db: Session = Depends(get_db)):
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    if payload.display_name is not None:
        brand.display_name = payload.display_name.strip()
    if payload.is_active is not None:
        brand.is_active = payload.is_active

    db.commit()
    db.refresh(brand)
    return brand

@router.delete("/{brand_id}", status_code=204)
def delete_brand(brand_id: str, db: Session = Depends(get_db)):
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
 
    # Step 1 — content drafts (brand_id is String, safe direct comparison)
    db.execute(delete(ContentDraft).where(ContentDraft.brand_id == brand_id))
 
    # Step 2 — topic chats (brand_id is String, safe direct comparison)
    db.execute(delete(TopicChat).where(TopicChat.brand_id == brand_id))
 
    # Step 3 — brand profile (String PK, no FK cascade)
    db.execute(delete(BrandProfile).where(BrandProfile.brand_id == brand_id))
 
    # Step 4 — media assets: brand_id column is UUID in DB but Brand.id is
    # a plain string slug. SQLAlchemy tries to cast the string to UUID and
    # PostgreSQL rejects it. Use raw SQL to compare as text instead.
    db.execute(text("""
        UPDATE media_assets
        SET brand_id = NULL, brand_name = NULL
        WHERE brand_id::text = :brand_id
    """), {"brand_id": brand_id})
 
    # Step 5 — brand itself
    db.delete(brand)
    db.commit()