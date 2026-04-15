"""
app/routers/org_profile.py
───────────────────────────
Org profile management endpoints.

Mount in main.py:
    from app.routers import org_profile
    app.include_router(org_profile.router)
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.dependencies.org import get_current_org, require_role
from app.models.organisation import Organisation
from app.models.org_profile import (
    OrgSponsor, OrgReview, OrgBusinessInfo,
    OrgCampaignGoal, OrgOffer, OrgAccreditation, OrgMetadata,
)

router = APIRouter(prefix="/org-profile", tags=["org-profile"])

PRESET_GOALS = [
    "Brand Awareness",
    "Lead Generation",
    "Sales & Conversions",
    "Community Engagement",
    "Customer Retention",
    "Product Launch",
    "Event Promotion",
    "Thought Leadership",
]


# ── Schemas ───────────────────────────────────────────────────────────────────

class SponsorIn(BaseModel):
    name:       str
    logo_url:   Optional[str] = None
    website:    Optional[str] = None
    sort_order: int           = 0
    is_active:  bool          = True

class SponsorPatch(BaseModel):
    name:       Optional[str]  = None
    logo_url:   Optional[str]  = None
    website:    Optional[str]  = None
    sort_order: Optional[int]  = None
    is_active:  Optional[bool] = None


class ReviewIn(BaseModel):
    author_name: str
    rating:      float
    body:        Optional[str]  = None
    source:      Optional[str]  = None
    review_date: Optional[date] = None
    is_featured: bool           = False

class ReviewPatch(BaseModel):
    author_name: Optional[str]   = None
    rating:      Optional[float] = None
    body:        Optional[str]   = None
    source:      Optional[str]   = None
    review_date: Optional[date]  = None
    is_featured: Optional[bool]  = None


class BusinessInfoIn(BaseModel):
    # identity
    business_type:   Optional[str] = None
    founded_year:    Optional[int] = None
    company_size:    Optional[str] = None
    tagline:         Optional[str] = None
    description:     Optional[str] = None
    registration_no: Optional[str] = None
    vat_number:      Optional[str] = None
    # contact
    email_primary:   Optional[str] = None
    email_support:   Optional[str] = None
    phone_primary:   Optional[str] = None
    phone_secondary: Optional[str] = None
    whatsapp:        Optional[str] = None
    website:         Optional[str] = None
    # location
    address:         Optional[str] = None
    city:            Optional[str] = None
    state_province:  Optional[str] = None
    postal_code:     Optional[str] = None
    country:         Optional[str] = None
    map_url:         Optional[str] = None
    # social
    facebook_url:    Optional[str] = None
    instagram_url:   Optional[str] = None
    linkedin_url:    Optional[str] = None
    twitter_url:     Optional[str] = None
    tiktok_url:      Optional[str] = None
    youtube_url:     Optional[str] = None


class GoalIn(BaseModel):
    label:     str
    is_active: bool = True

class GoalPatch(BaseModel):
    label:     Optional[str]  = None
    is_active: Optional[bool] = None


class OfferIn(BaseModel):
    title:       str
    description: Optional[str]  = None
    cta_text:    Optional[str]  = None
    cta_url:     Optional[str]  = None
    expires_at:  Optional[date] = None
    is_active:   bool           = True

class OfferPatch(BaseModel):
    title:       Optional[str]  = None
    description: Optional[str]  = None
    cta_text:    Optional[str]  = None
    cta_url:     Optional[str]  = None
    expires_at:  Optional[date] = None
    is_active:   Optional[bool] = None


class AccreditationIn(BaseModel):
    name:      str
    issuer:    Optional[str] = None
    year:      Optional[int] = None
    logo_url:  Optional[str] = None
    is_active: bool          = True

class AccreditationPatch(BaseModel):
    name:      Optional[str]  = None
    issuer:    Optional[str]  = None
    year:      Optional[int]  = None
    logo_url:  Optional[str]  = None
    is_active: Optional[bool] = None


class MetadataIn(BaseModel):
    key:      str
    value:    str
    category: Optional[str] = None

class MetadataPatch(BaseModel):
    key:      Optional[str] = None
    value:    Optional[str] = None
    category: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# SPONSORS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/sponsors")
def list_sponsors(
    org: Organisation = Depends(get_current_org),
    db:  Session      = Depends(get_db),
):
    rows = db.execute(
        select(OrgSponsor)
        .where(OrgSponsor.org_id == org.id)
        .order_by(OrgSponsor.sort_order.asc(), OrgSponsor.created_at.asc())
    ).scalars().all()
    return [r.to_dict() for r in rows]


@router.post("/sponsors", status_code=201)
def create_sponsor(
    payload: SponsorIn,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = OrgSponsor(org_id=org.id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row.to_dict()


@router.patch("/sponsors/{sponsor_id}")
def update_sponsor(
    sponsor_id: str,
    payload:    SponsorPatch,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = _get_or_404(db, OrgSponsor, sponsor_id, org.id)
    _apply_patch(row, payload)
    db.commit(); db.refresh(row)
    return row.to_dict()


@router.delete("/sponsors/{sponsor_id}", status_code=204)
def delete_sponsor(
    sponsor_id: str,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = _get_or_404(db, OrgSponsor, sponsor_id, org.id)
    db.delete(row); db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# REVIEWS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/reviews")
def list_reviews(
    org: Organisation = Depends(get_current_org),
    db:  Session      = Depends(get_db),
):
    rows = db.execute(
        select(OrgReview)
        .where(OrgReview.org_id == org.id)
        .order_by(OrgReview.is_featured.desc(), OrgReview.created_at.desc())
    ).scalars().all()
    return [r.to_dict() for r in rows]


@router.post("/reviews", status_code=201)
def create_review(
    payload: ReviewIn,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    if not (1.0 <= payload.rating <= 5.0):
        raise HTTPException(400, "Rating must be between 1 and 5")
    row = OrgReview(org_id=org.id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row.to_dict()


@router.patch("/reviews/{review_id}")
def update_review(
    review_id: str,
    payload:   ReviewPatch,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = _get_or_404(db, OrgReview, review_id, org.id)
    _apply_patch(row, payload)
    db.commit(); db.refresh(row)
    return row.to_dict()


@router.delete("/reviews/{review_id}", status_code=204)
def delete_review(
    review_id: str,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = _get_or_404(db, OrgReview, review_id, org.id)
    db.delete(row); db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS INFO  (upsert — one row per org)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/business-info")
def get_business_info(
    org: Organisation = Depends(get_current_org),
    db:  Session      = Depends(get_db),
):
    row = db.execute(
        select(OrgBusinessInfo).where(OrgBusinessInfo.org_id == org.id)
    ).scalars().first()
    return row.to_dict() if row else {}


@router.put("/business-info")
def upsert_business_info(
    payload: BusinessInfoIn,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = db.execute(
        select(OrgBusinessInfo).where(OrgBusinessInfo.org_id == org.id)
    ).scalars().first()
    if not row:
        row = OrgBusinessInfo(id=uuid.uuid4(), org_id=org.id)
        db.add(row)
    _apply_patch(row, payload)
    db.commit(); db.refresh(row)
    return row.to_dict()


# ─────────────────────────────────────────────────────────────────────────────
# CAMPAIGN GOALS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/campaign-goals")
def list_campaign_goals(
    org: Organisation = Depends(get_current_org),
    db:  Session      = Depends(get_db),
):
    rows = db.execute(
        select(OrgCampaignGoal)
        .where(OrgCampaignGoal.org_id == org.id)
        .order_by(OrgCampaignGoal.sort_order.asc(), OrgCampaignGoal.created_at.asc())
    ).scalars().all()
    return {
        "presets":  PRESET_GOALS,
        "selected": [r.to_dict() for r in rows],
    }


@router.post("/campaign-goals", status_code=201)
def add_campaign_goal(
    payload: GoalIn,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    is_preset = payload.label in PRESET_GOALS
    row = OrgCampaignGoal(
        org_id=org.id,
        label=payload.label,
        is_preset=is_preset,
        is_active=payload.is_active,
    )
    db.add(row); db.commit(); db.refresh(row)
    return row.to_dict()


@router.patch("/campaign-goals/{goal_id}")
def update_campaign_goal(
    goal_id: str,
    payload: GoalPatch,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = _get_or_404(db, OrgCampaignGoal, goal_id, org.id)
    _apply_patch(row, payload)
    db.commit(); db.refresh(row)
    return row.to_dict()


@router.delete("/campaign-goals/{goal_id}", status_code=204)
def delete_campaign_goal(
    goal_id: str,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = _get_or_404(db, OrgCampaignGoal, goal_id, org.id)
    db.delete(row); db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# OFFERS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/offers")
def list_offers(
    org: Organisation = Depends(get_current_org),
    db:  Session      = Depends(get_db),
):
    rows = db.execute(
        select(OrgOffer)
        .where(OrgOffer.org_id == org.id)
        .order_by(OrgOffer.is_active.desc(), OrgOffer.created_at.desc())
    ).scalars().all()
    return [r.to_dict() for r in rows]


@router.post("/offers", status_code=201)
def create_offer(
    payload: OfferIn,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = OrgOffer(org_id=org.id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row.to_dict()


@router.patch("/offers/{offer_id}")
def update_offer(
    offer_id: str,
    payload:  OfferPatch,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = _get_or_404(db, OrgOffer, offer_id, org.id)
    _apply_patch(row, payload)
    db.commit(); db.refresh(row)
    return row.to_dict()


@router.delete("/offers/{offer_id}", status_code=204)
def delete_offer(
    offer_id: str,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = _get_or_404(db, OrgOffer, offer_id, org.id)
    db.delete(row); db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# ACCREDITATIONS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/accreditations")
def list_accreditations(
    org: Organisation = Depends(get_current_org),
    db:  Session      = Depends(get_db),
):
    rows = db.execute(
        select(OrgAccreditation)
        .where(OrgAccreditation.org_id == org.id)
        .order_by(OrgAccreditation.year.desc().nulls_last(), OrgAccreditation.created_at.desc())
    ).scalars().all()
    return [r.to_dict() for r in rows]


@router.post("/accreditations", status_code=201)
def create_accreditation(
    payload: AccreditationIn,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = OrgAccreditation(org_id=org.id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row.to_dict()


@router.patch("/accreditations/{accreditation_id}")
def update_accreditation(
    accreditation_id: str,
    payload:          AccreditationPatch,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = _get_or_404(db, OrgAccreditation, accreditation_id, org.id)
    _apply_patch(row, payload)
    db.commit(); db.refresh(row)
    return row.to_dict()


@router.delete("/accreditations/{accreditation_id}", status_code=204)
def delete_accreditation(
    accreditation_id: str,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = _get_or_404(db, OrgAccreditation, accreditation_id, org.id)
    db.delete(row); db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# METADATA STRIP
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/metadata")
def list_metadata(
    org: Organisation = Depends(get_current_org),
    db:  Session      = Depends(get_db),
):
    rows = db.execute(
        select(OrgMetadata)
        .where(OrgMetadata.org_id == org.id)
        .order_by(OrgMetadata.category.asc().nulls_last(), OrgMetadata.created_at.asc())
    ).scalars().all()
    return [r.to_dict() for r in rows]


@router.post("/metadata", status_code=201)
def create_metadata(
    payload: MetadataIn,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = OrgMetadata(org_id=org.id, **payload.model_dump())
    db.add(row); db.commit(); db.refresh(row)
    return row.to_dict()


@router.patch("/metadata/{metadata_id}")
def update_metadata(
    metadata_id: str,
    payload:     MetadataPatch,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = _get_or_404(db, OrgMetadata, metadata_id, org.id)
    _apply_patch(row, payload)
    db.commit(); db.refresh(row)
    return row.to_dict()


@router.delete("/metadata/{metadata_id}", status_code=204)
def delete_metadata(
    metadata_id: str,
    org: Organisation = Depends(require_role("owner", "admin")),
    db:  Session      = Depends(get_db),
):
    row = _get_or_404(db, OrgMetadata, metadata_id, org.id)
    db.delete(row); db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_or_404(db: Session, Model, row_id: str, org_id):
    try:
        uid = uuid.UUID(row_id)
    except ValueError:
        raise HTTPException(400, "Invalid ID format")
    row = db.execute(
        select(Model).where(Model.id == uid, Model.org_id == org_id)
    ).scalars().first()
    if not row:
        raise HTTPException(404, f"{Model.__tablename__} item not found")
    return row


def _apply_patch(row, payload):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)