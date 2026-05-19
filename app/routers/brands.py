from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, text

from app.database import get_db
from app.models.brand import Brand
from app.schemas.brand import BrandCreate, BrandUpdate, BrandOut
from app.models.brand_profile import BrandProfile
from app.models.topic_chat import TopicChat
from app.models.content_draft import ContentDraft
from app.dependencies.org import get_current_org, require_role
from app.models.organisation import Organisation

import uuid

router = APIRouter(prefix="/brands", tags=["brands"])


def _clean_id(value: str | None) -> str:
    if not value:
        return str(uuid.uuid4())

    cleaned = (
        value.strip()
        .lower()
        .replace(" ", "-")
        .replace("_", "-")
    )

    cleaned = "".join(ch for ch in cleaned if ch.isalnum() or ch == "-")
    cleaned = cleaned.strip("-")

    return cleaned or str(uuid.uuid4())


def _clean_hex(value: str | None, fallback: str = "#7c3aed") -> str | None:
    if value is None:
        return None

    value = value.strip()

    if not value:
        return fallback

    if not value.startswith("#"):
        value = f"#{value}"

    if len(value) != 7:
        return fallback

    return value


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()

    return value or None


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
    brand_id = _clean_id(payload.id)

    existing = db.execute(
        select(Brand).where(
            Brand.id == brand_id,
            Brand.org_id == org.id,
        )
    ).scalars().first()

    if existing:
        raise HTTPException(status_code=400, detail="Brand already exists")

    brand = Brand(
        id=brand_id,
        display_name=payload.display_name.strip(),
        is_active=payload.is_active,
        org_id=org.id,

        tones=payload.tones or [],

        logo_url=_clean_text(payload.logo_url),
        primary_color=_clean_hex(payload.primary_color, "#7c3aed"),
        secondary_color=_clean_hex(payload.secondary_color, None),

        tagline=_clean_text(payload.tagline),
        description=_clean_text(payload.description),
        industry=_clean_text(payload.industry),
        target_audience=_clean_text(payload.target_audience),

        website_url=_clean_text(payload.website_url),
        email=_clean_text(payload.email),
        phone=_clean_text(payload.phone),
        address=_clean_text(payload.address),

        facebook_url=_clean_text(payload.facebook_url),
        instagram_url=_clean_text(payload.instagram_url),
        linkedin_url=_clean_text(payload.linkedin_url),
        twitter_url=_clean_text(payload.twitter_url),
        tiktok_url=_clean_text(payload.tiktok_url),
        youtube_url=_clean_text(payload.youtube_url),

        font_primary=_clean_text(payload.font_primary),
        font_secondary=_clean_text(payload.font_secondary),

        brand_values=payload.brand_values or [],
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

    data = payload.model_dump(exclude_unset=True)

    if "display_name" in data:
        brand.display_name = payload.display_name.strip()

    if "is_active" in data:
        brand.is_active = payload.is_active

    if "tones" in data:
        brand.tones = payload.tones or []

    if "logo_url" in data:
        brand.logo_url = _clean_text(payload.logo_url)

    if "primary_color" in data:
        brand.primary_color = _clean_hex(payload.primary_color, "#7c3aed")

    if "secondary_color" in data:
        brand.secondary_color = _clean_hex(payload.secondary_color, None)

    text_fields = [
        "tagline",
        "description",
        "industry",
        "target_audience",
        "website_url",
        "email",
        "phone",
        "address",
        "facebook_url",
        "instagram_url",
        "linkedin_url",
        "twitter_url",
        "tiktok_url",
        "youtube_url",
        "font_primary",
        "font_secondary",
    ]

    for field in text_fields:
        if field in data:
            setattr(brand, field, _clean_text(getattr(payload, field)))

    if "brand_values" in data:
        brand.brand_values = payload.brand_values or []

    db.commit()
    db.refresh(brand)

    return brand


@router.delete("/{brand_id}", status_code=204)
def delete_brand(
    brand_id: str,
    org: Organisation = Depends(require_role("owner", "admin")),
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

    db.execute(
        delete(ContentDraft).where(
            ContentDraft.brand_id == brand_id,
            ContentDraft.org_id == org.id,
        )
    )

    db.execute(
        delete(TopicChat).where(
            TopicChat.brand_id == brand_id,
            TopicChat.org_id == org.id,
        )
    )

    db.execute(delete(BrandProfile).where(BrandProfile.brand_id == brand_id))

    db.execute(
        text("""
            UPDATE media_assets
            SET brand_id = NULL, brand_name = NULL
            WHERE brand_id::text = :brand_id
            AND org_id = :org_id
        """),
        {
            "brand_id": brand_id,
            "org_id": str(org.id),
        },
    )

    db.delete(brand)
    db.commit()