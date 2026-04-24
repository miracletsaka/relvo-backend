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
from app.dependencies.org import get_current_org, require_role
from app.models.organisation import Organisation
import uuid

router = APIRouter(prefix="/brands", tags=["brands"])


@router.get("", response_model=list[BrandOut])
def list_brands(
    active_only: bool = True,
    org: Organisation = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    q = select(Brand).where(Brand.org_id == org.id)
    if active_only:
        q = q.where(Brand.is_active == True)  # noqa
    return db.execute(q).scalars().all()


@router.post("", response_model=BrandOut)
def create_brand(
    payload: BrandCreate,
    org: Organisation = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    brand = Brand(
        id=str(uuid.uuid4()),
        display_name=payload.display_name.strip(),
        is_active=payload.is_active,
        org_id=org.id,
        logo_url=payload.logo_url,
        primary_color=payload.primary_color,
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


@router.patch("/{brand_id}", response_model=BrandOut)
def update_brand(
    brand_id: str,
    payload: BrandUpdate,
    org: Organisation = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    brand = db.execute(
        select(Brand).where(
            Brand.id == brand_id,
            Brand.org_id == org.id,
        )
    ).scalars().first()

    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    if payload.display_name is not None:
        brand.display_name = payload.display_name.strip()

    if payload.is_active is not None:
        brand.is_active = payload.is_active

    if payload.logo_url is not None:
        brand.logo_url = payload.logo_url.strip() if payload.logo_url else None

    if payload.primary_color is not None:
        brand.primary_color = payload.primary_color.strip() if payload.primary_color else "#7c3aed"

    db.commit()
    db.refresh(brand)
    return brand


@router.delete("/{brand_id}", status_code=204)
def delete_brand(
    brand_id: str,
    org: Organisation = Depends(require_role("owner", "admin")),  # only admins can delete
    db: Session = Depends(get_db),
):
    brand = db.execute(
        select(Brand).where(
            Brand.id     == brand_id,
            Brand.org_id == org.id,           # ← must belong to this org
        )
    ).scalars().first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Step 1 — content drafts
    db.execute(delete(ContentDraft).where(
        ContentDraft.brand_id == brand_id,
        ContentDraft.org_id   == org.id,      # ← extra safety check
    ))

    # Step 2 — topic chats
    db.execute(delete(TopicChat).where(
        TopicChat.brand_id == brand_id,
        TopicChat.org_id   == org.id,
    ))

    # Step 3 — brand profile
    db.execute(delete(BrandProfile).where(BrandProfile.brand_id == brand_id))

    # Step 4 — media assets (raw SQL keeps the UUID/text cast fix you already had)
    db.execute(text("""
        UPDATE media_assets
        SET brand_id = NULL, brand_name = NULL
        WHERE brand_id::text = :brand_id
        AND   org_id  = :org_id
    """), {"brand_id": brand_id, "org_id": str(org.id)})

    # Step 5 — brand itself
    db.delete(brand)
    db.commit()