"""
app/services/org_data_loader.py
────────────────────────────────
Loads real org profile data from the database to inject into
structured content output — replacing AI-hallucinated values.

Usage:
    from app.services.org_data_loader import load_org_context
    ctx = load_org_context(db, org_id)
    # ctx is an OrgContext dataclass ready to merge into structured output
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.org_profile import (
    OrgBusinessInfo,
    OrgReview,
    OrgOffer,
    OrgSponsor,
    OrgAccreditation,
    OrgMetadata,
    OrgCampaignGoal,
)


# ── Output shape ──────────────────────────────────────────────────────────────

@dataclass
class OrgContext:
    # Business info
    business_tagline: Optional[str] = None
    business_description: Optional[str] = None
    business_type: Optional[str] = None
    business_website: Optional[str] = None
    business_address: Optional[str] = None
    business_founded: Optional[int] = None
    business_size: Optional[str] = None

    # Contact / communication
    email_primary: Optional[str] = None
    email_support: Optional[str] = None
    phone_primary: Optional[str] = None
    phone_secondary: Optional[str] = None
    whatsapp: Optional[str] = None

    # Location
    city: Optional[str] = None
    country: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    map_url: Optional[str] = None

    # Socials
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    youtube_url: Optional[str] = None

    # Legal
    registration_no: Optional[str] = None
    vat_number: Optional[str] = None

    # Best review (featured first, then highest rated)
    review_text: Optional[str] = None
    review_author: Optional[str] = None
    review_rating: Optional[float] = None
    review_source: Optional[str] = None

    # All active reviews (for templates that show multiple)
    reviews: list = field(default_factory=list)

    # Best active offer
    offer_title: Optional[str] = None
    offer_cta: Optional[str] = None
    offer_url: Optional[str] = None
    offer_desc: Optional[str] = None
    offer_expires: Optional[str] = None

    # All active offers
    offers: list = field(default_factory=list)

    # Active sponsors
    sponsors: list = field(default_factory=list)

    # Active accreditations
    accreditations: list = field(default_factory=list)

    # Active campaign goals
    campaign_goals: list = field(default_factory=list)

    # Metadata as a dict {key: value} for AI prompt injection
    metadata_dict: dict = field(default_factory=dict)

    # Raw metadata rows for structured output
    metadata: list = field(default_factory=list)

    def to_ai_context_block(self) -> str:
        """
        Returns a formatted block to inject into the AI system/user prompt
        so the AI is aware of real org context when generating copy.
        """
        lines = ["ORG PROFILE CONTEXT (real data — use this to inform copy):"]

        if self.business_tagline:
            lines.append(f"Tagline: {self.business_tagline}")
        if self.business_description:
            lines.append(f"Business description: {self.business_description}")
        if self.business_type:
            lines.append(f"Business type: {self.business_type}")
        if self.business_website:
            lines.append(f"Website: {self.business_website}")
        if self.business_address:
            lines.append(f"Address: {self.business_address}")
        if self.city or self.country or self.state_province:
            location_parts = [self.city, self.state_province, self.country]
            location_text = ", ".join(p for p in location_parts if p)
            if location_text:
                lines.append(f"Location: {location_text}")

        if self.phone_primary:
            lines.append(f"Primary phone: {self.phone_primary}")
        if self.phone_secondary:
            lines.append(f"Secondary phone: {self.phone_secondary}")
        if self.whatsapp:
            lines.append(f"WhatsApp: {self.whatsapp}")
        if self.email_primary:
            lines.append(f"Primary email: {self.email_primary}")
        if self.email_support:
            lines.append(f"Support email: {self.email_support}")

        if self.facebook_url:
            lines.append(f"Facebook: {self.facebook_url}")
        if self.instagram_url:
            lines.append(f"Instagram: {self.instagram_url}")
        if self.linkedin_url:
            lines.append(f"LinkedIn: {self.linkedin_url}")
        if self.twitter_url:
            lines.append(f"Twitter/X: {self.twitter_url}")
        if self.tiktok_url:
            lines.append(f"TikTok: {self.tiktok_url}")
        if self.youtube_url:
            lines.append(f"YouTube: {self.youtube_url}")
        if self.map_url:
            lines.append(f"Map URL: {self.map_url}")

        if self.registration_no:
            lines.append(f"Registration number: {self.registration_no}")
        if self.vat_number:
            lines.append(f"VAT number: {self.vat_number}")

        if self.review_text and self.review_author:
            lines.append(f'Featured review: "{self.review_text}" — {self.review_author}')

        if self.offer_title:
            lines.append(
                f"Current offer: {self.offer_title}"
                + (f" | CTA: {self.offer_cta}" if self.offer_cta else "")
            )

        if self.sponsors:
            names = ", ".join(s.get("name", "") for s in self.sponsors if s.get("name"))
            if names:
                lines.append(f"Sponsors / partners: {names}")

        if self.accreditations:
            names = ", ".join(a.get("name", "") for a in self.accreditations if a.get("name"))
            if names:
                lines.append(f"Accreditations / certifications: {names}")

        if self.campaign_goals:
            labels = ", ".join(g.get("label", "") for g in self.campaign_goals if g.get("label"))
            if labels:
                lines.append(f"Campaign goals: {labels}")

        if self.metadata_dict:
            lines.append("Additional context:")
            for k, v in self.metadata_dict.items():
                lines.append(f"  {k}: {v}")

        return "\n".join(lines)

    def to_structured_patch(self) -> dict:
        """
        Returns a dict of fields to OVERWRITE on the AI-generated structured
        output. These are the real values that replace any AI-hallucinated ones.
        """
        patch: dict = {}

        # Business info — always overwrite with real data
        if self.business_tagline is not None:
            patch["business_tagline"] = self.business_tagline
        if self.business_description is not None:
            patch["business_description"] = self.business_description
        if self.business_type is not None:
            patch["business_type"] = self.business_type
        if self.business_website is not None:
            patch["business_website"] = self.business_website
            patch["website"] = self.business_website
        if self.business_address is not None:
            patch["business_address"] = self.business_address
            patch["address"] = self.business_address
        if self.business_founded is not None:
            patch["business_founded"] = self.business_founded
        if self.business_size is not None:
            patch["business_size"] = self.business_size

        # Contact
        if self.email_primary is not None:
            patch["email_primary"] = self.email_primary
            patch["email"] = self.email_primary
        if self.email_support is not None:
            patch["email_support"] = self.email_support
        if self.phone_primary is not None:
            patch["phone_primary"] = self.phone_primary
            patch["phone"] = self.phone_primary
        if self.phone_secondary is not None:
            patch["phone_secondary"] = self.phone_secondary
        if self.whatsapp is not None:
            patch["whatsapp"] = self.whatsapp

        # Location
        if self.city is not None:
            patch["city"] = self.city
        if self.country is not None:
            patch["country"] = self.country
        if self.state_province is not None:
            patch["state_province"] = self.state_province
        if self.postal_code is not None:
            patch["postal_code"] = self.postal_code
        if self.map_url is not None:
            patch["map_url"] = self.map_url

        full_address_parts = [
            self.business_address,
            self.city,
            self.state_province,
            self.postal_code,
            self.country,
        ]
        full_address = ", ".join(p for p in full_address_parts if p)
        if full_address:
            patch["fullAddress"] = full_address

        # Socials
        if self.facebook_url is not None:
            patch["facebook_url"] = self.facebook_url
        if self.instagram_url is not None:
            patch["instagram_url"] = self.instagram_url
        if self.linkedin_url is not None:
            patch["linkedin_url"] = self.linkedin_url
        if self.twitter_url is not None:
            patch["twitter_url"] = self.twitter_url
        if self.tiktok_url is not None:
            patch["tiktok_url"] = self.tiktok_url
        if self.youtube_url is not None:
            patch["youtube_url"] = self.youtube_url

        # Legal
        if self.registration_no is not None:
            patch["registration_no"] = self.registration_no
        if self.vat_number is not None:
            patch["vat_number"] = self.vat_number

        # Review — overwrite with real featured/top review
        if self.review_text is not None:
            patch["review_text"] = self.review_text
        if self.review_author is not None:
            patch["review_author"] = self.review_author

        # Offer — overwrite with real active offer
        if self.offer_title is not None:
            patch["offer_title"] = self.offer_title
        if self.offer_cta is not None:
            patch["offer_cta"] = self.offer_cta

        # Arrays — always inject real data
        patch["sponsors"] = self.sponsors
        patch["accreditations"] = self.accreditations
        patch["reviews"] = self.reviews
        patch["offers"] = self.offers
        patch["metadata"] = self.metadata
        patch["campaign_goals"] = self.campaign_goals

        return patch


# ── Loader ────────────────────────────────────────────────────────────────────

def load_org_context(db: Session, org_id: uuid.UUID) -> OrgContext:
    """
    Loads all org profile data from the DB and returns an OrgContext.
    Call this once before generating a post, then:
      1. Pass ctx.to_ai_context_block() into the AI prompt
      2. After AI returns, merge ctx.to_structured_patch() into structured output
    """
    ctx = OrgContext()

    # ── Business info ─────────────────────────────────────────────────────────
    biz = db.execute(
        select(OrgBusinessInfo).where(OrgBusinessInfo.org_id == org_id)
    ).scalars().first()

    if biz:
        ctx.business_tagline = biz.tagline
        ctx.business_description = biz.description
        ctx.business_type = biz.business_type
        ctx.business_website = biz.website
        ctx.business_address = biz.address
        ctx.business_founded = biz.founded_year
        ctx.business_size = biz.company_size

        # Contact
        ctx.email_primary = biz.email_primary
        ctx.email_support = biz.email_support
        ctx.phone_primary = biz.phone_primary
        ctx.phone_secondary = biz.phone_secondary
        ctx.whatsapp = biz.whatsapp

        # Location
        ctx.city = biz.city
        ctx.country = biz.country
        ctx.state_province = biz.state_province
        ctx.postal_code = biz.postal_code
        ctx.map_url = biz.map_url

        # Socials
        ctx.facebook_url = biz.facebook_url
        ctx.instagram_url = biz.instagram_url
        ctx.linkedin_url = biz.linkedin_url
        ctx.twitter_url = biz.twitter_url
        ctx.tiktok_url = biz.tiktok_url
        ctx.youtube_url = biz.youtube_url

        # Legal
        ctx.registration_no = biz.registration_no
        ctx.vat_number = biz.vat_number

    # ── Reviews ───────────────────────────────────────────────────────────────
    reviews = db.execute(
        select(OrgReview)
        .where(OrgReview.org_id == org_id)
        .order_by(
            OrgReview.is_featured.desc(),
            OrgReview.rating.desc(),
            OrgReview.created_at.desc(),
        )
    ).scalars().all()

    ctx.reviews = [
        {
            "author_name": r.author_name,
            "rating": r.rating,
            "body": r.body,
            "source": r.source,
            "is_featured": r.is_featured,
        }
        for r in reviews
    ]

    if reviews:
        best = reviews[0]
        ctx.review_text = best.body
        ctx.review_author = best.author_name
        ctx.review_rating = best.rating
        ctx.review_source = best.source

    # ── Offers ────────────────────────────────────────────────────────────────
    from datetime import date

    offers = db.execute(
        select(OrgOffer)
        .where(OrgOffer.org_id == org_id)
        .where(OrgOffer.is_active == True)  # noqa: E712
        .order_by(OrgOffer.created_at.desc())
    ).scalars().all()

    # Filter out expired offers
    today = date.today()
    active_offers = [
        o for o in offers
        if o.expires_at is None or o.expires_at >= today
    ]

    ctx.offers = [
        {
            "title": o.title,
            "description": o.description,
            "cta_text": o.cta_text,
            "cta_url": o.cta_url,
            "expires_at": o.expires_at.isoformat() if o.expires_at else None,
        }
        for o in active_offers
    ]

    if active_offers:
        best_offer = active_offers[0]
        ctx.offer_title = best_offer.title
        ctx.offer_cta = best_offer.cta_text
        ctx.offer_url = best_offer.cta_url
        ctx.offer_desc = best_offer.description
        ctx.offer_expires = best_offer.expires_at.isoformat() if best_offer.expires_at else None

    # ── Sponsors ──────────────────────────────────────────────────────────────
    sponsors = db.execute(
        select(OrgSponsor)
        .where(OrgSponsor.org_id == org_id)
        .where(OrgSponsor.is_active == True)  # noqa: E712
        .order_by(OrgSponsor.sort_order.asc(), OrgSponsor.created_at.asc())
    ).scalars().all()

    ctx.sponsors = [
        {
            "name": s.name,
            "logo_url": s.logo_url,
            "website": s.website,
        }
        for s in sponsors
    ]

    # ── Accreditations ────────────────────────────────────────────────────────
    accreditations = db.execute(
        select(OrgAccreditation)
        .where(OrgAccreditation.org_id == org_id)
        .where(OrgAccreditation.is_active == True)  # noqa: E712
        .order_by(OrgAccreditation.year.desc().nulls_last(), OrgAccreditation.created_at.asc())
    ).scalars().all()

    ctx.accreditations = [
        {
            "name": a.name,
            "issuer": a.issuer,
            "year": a.year,
            "logo_url": a.logo_url,
        }
        for a in accreditations
    ]

    # ── Campaign Goals ────────────────────────────────────────────────────────
    goals = db.execute(
        select(OrgCampaignGoal)
        .where(OrgCampaignGoal.org_id == org_id)
        .where(OrgCampaignGoal.is_active == True)  # noqa: E712
        .order_by(OrgCampaignGoal.sort_order.asc(), OrgCampaignGoal.created_at.asc())
    ).scalars().all()

    ctx.campaign_goals = [
        {"label": g.label, "is_preset": g.is_preset}
        for g in goals
    ]

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata = db.execute(
        select(OrgMetadata)
        .where(OrgMetadata.org_id == org_id)
        .order_by(OrgMetadata.category.asc().nulls_last(), OrgMetadata.created_at.asc())
    ).scalars().all()

    ctx.metadata = [
        {"key": m.key, "value": m.value, "category": m.category}
        for m in metadata
    ]

    # Build flat dict for prompt injection (all categories)
    ctx.metadata_dict = {m.key: m.value for m in metadata}

    return ctx