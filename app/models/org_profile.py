"""
app/models/org_profile.py
──────────────────────────
Models for org-level profile data:
  - OrgSponsor
  - OrgReview
  - OrgBusinessInfo
  - OrgCampaignGoal
  - OrgOffer
  - OrgAccreditation
  - OrgMetadata
"""
from __future__ import annotations

import uuid
from datetime import datetime, date

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float,
    ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


# ── Sponsors ──────────────────────────────────────────────────────────────────

class OrgSponsor(Base):
    __tablename__ = "org_sponsors"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id     = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    name       = Column(String(200), nullable=False)
    logo_url   = Column(Text, nullable=True)
    website    = Column(String(500), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id":         str(self.id),
            "org_id":     str(self.org_id),
            "name":       self.name,
            "logo_url":   self.logo_url,
            "website":    self.website,
            "sort_order": self.sort_order,
            "is_active":  self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Reviews ───────────────────────────────────────────────────────────────────

import uuid
from sqlalchemy import Column, String, Float, Text, Date, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

class OrgReview(Base):
    __tablename__ = "org_reviews"
 
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id          = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
 
    # Core review data
    author_name     = Column(String(200), nullable=False)
    rating          = Column(Float, nullable=False)
    body            = Column(Text, nullable=True)
    source          = Column(String(100), nullable=True, default="Website")
    review_date     = Column(DateTime(timezone=True), nullable=True)
 
    # Flags
    is_featured     = Column(Boolean, default=False, nullable=False)
    is_verified     = Column(Boolean, default=False, nullable=False)
    reviewer_email  = Column(String(320), nullable=True)
 
    # ── NEW: source images uploaded by reviewer ───────────────────────────────
    reviewer_photo_url  = Column(Text, nullable=True)   # identity/profile photo
    product_image_url   = Column(Text, nullable=True)   # product/showcase image
 
    # ── NEW: generated review card image ─────────────────────────────────────
    card_image_url  = Column(Text, nullable=True)
    card_status     = Column(String(20), nullable=True, default="pending")
    # card_status: 'pending' | 'generated' | 'failed'
 
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
 
    def to_dict(self):
        return {
            "id":                  str(self.id),
            "org_id":              str(self.org_id),
            "author_name":         self.author_name,
            "rating":              self.rating,
            "body":                self.body,
            "source":              self.source,
            "review_date":         self.review_date.isoformat()  if self.review_date  else None,
            "is_featured":         self.is_featured,
            "is_verified":         self.is_verified,
            "reviewer_photo_url":  self.reviewer_photo_url,
            "product_image_url":   self.product_image_url,
            "card_image_url":      self.card_image_url,
            "card_status":         self.card_status,
            "created_at":          self.created_at.isoformat()   if self.created_at   else None,
            "updated_at":          self.updated_at.isoformat()   if self.updated_at   else None,
        }


# ── Business Info (one row per org) ──────────────────────────────────────────

class OrgBusinessInfo(Base):
    __tablename__ = "org_business_info"
 
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id          = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
 
    # ── Identity ──────────────────────────────────────────────────────────────
    business_type   = Column(String(100), nullable=True)
    founded_year    = Column(Integer, nullable=True)
    company_size    = Column(String(50), nullable=True)
    tagline         = Column(String(300), nullable=True)
    description     = Column(Text, nullable=True)
    registration_no = Column(String(100), nullable=True)
    vat_number      = Column(String(100), nullable=True)
 
    # ── Contact ───────────────────────────────────────────────────────────────
    email_primary   = Column(String(320), nullable=True)
    email_support   = Column(String(320), nullable=True)
    phone_primary   = Column(String(30), nullable=True)    # includes country code e.g. +44 7911 123456
    phone_secondary = Column(String(30), nullable=True)
    whatsapp        = Column(String(30), nullable=True)
    website         = Column(String(500), nullable=True)
 
    # ── Location ──────────────────────────────────────────────────────────────
    address         = Column(Text, nullable=True)          # street line(s)
    city            = Column(String(100), nullable=True)
    state_province  = Column(String(100), nullable=True)
    postal_code     = Column(String(20), nullable=True)
    country         = Column(String(100), nullable=True)
    map_url         = Column(String(1000), nullable=True)  # Google Maps embed/link
 
    # ── Social ────────────────────────────────────────────────────────────────
    facebook_url    = Column(String(500), nullable=True)
    instagram_url   = Column(String(500), nullable=True)
    linkedin_url    = Column(String(500), nullable=True)
    twitter_url     = Column(String(500), nullable=True)
    tiktok_url      = Column(String(500), nullable=True)
    youtube_url     = Column(String(500), nullable=True)
 
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
 
    def to_dict(self):
        return {
            "id":              str(self.id),
            "org_id":          str(self.org_id),
            # identity
            "business_type":   self.business_type,
            "founded_year":    self.founded_year,
            "company_size":    self.company_size,
            "tagline":         self.tagline,
            "description":     self.description,
            "registration_no": self.registration_no,
            "vat_number":      self.vat_number,
            # contact
            "email_primary":   self.email_primary,
            "email_support":   self.email_support,
            "phone_primary":   self.phone_primary,
            "phone_secondary": self.phone_secondary,
            "whatsapp":        self.whatsapp,
            "website":         self.website,
            # location
            "address":         self.address,
            "city":            self.city,
            "state_province":  self.state_province,
            "postal_code":     self.postal_code,
            "country":         self.country,
            "map_url":         self.map_url,
            # social
            "facebook_url":    self.facebook_url,
            "instagram_url":   self.instagram_url,
            "linkedin_url":    self.linkedin_url,
            "twitter_url":     self.twitter_url,
            "tiktok_url":      self.tiktok_url,
            "youtube_url":     self.youtube_url,
            "created_at":      self.created_at.isoformat() if self.created_at else None,
            "updated_at":      self.updated_at.isoformat() if self.updated_at else None,
        }
 


# ── Campaign Goals ────────────────────────────────────────────────────────────

class OrgCampaignGoal(Base):
    __tablename__ = "org_campaign_goals"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id     = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    label      = Column(String(200), nullable=False)    # "Brand Awareness", custom, etc.
    is_preset  = Column(Boolean, default=False)         # True = system preset, False = custom
    is_active  = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id":         str(self.id),
            "org_id":     str(self.org_id),
            "label":      self.label,
            "is_preset":  self.is_preset,
            "is_active":  self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── Offers ────────────────────────────────────────────────────────────────────

class OrgOffer(Base):
    __tablename__ = "org_offers"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id      = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    title       = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    cta_text    = Column(String(100), nullable=True)     # "Book Now", "Get 20% Off", …
    cta_url     = Column(String(500), nullable=True)
    expires_at  = Column(Date, nullable=True)
    is_active   = Column(Boolean, default=True, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id":          str(self.id),
            "org_id":      str(self.org_id),
            "title":       self.title,
            "description": self.description,
            "cta_text":    self.cta_text,
            "cta_url":     self.cta_url,
            "expires_at":  self.expires_at.isoformat() if self.expires_at else None,
            "is_active":   self.is_active,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
            "updated_at":  self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Accreditations ────────────────────────────────────────────────────────────

class OrgAccreditation(Base):
    __tablename__ = "org_accreditations"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id     = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    name       = Column(String(200), nullable=False)      # "ISO 9001", "Google Partner", …
    issuer     = Column(String(200), nullable=True)
    year       = Column(Integer, nullable=True)
    logo_url   = Column(Text, nullable=True)
    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id":         str(self.id),
            "org_id":     str(self.org_id),
            "name":       self.name,
            "issuer":     self.issuer,
            "year":       self.year,
            "logo_url":   self.logo_url,
            "is_active":  self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Metadata Strip (key-value AI context) ────────────────────────────────────

class OrgMetadata(Base):
    __tablename__ = "org_metadata"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id     = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    key        = Column(String(200), nullable=False)    # "target_audience", "tone", …
    value      = Column(Text, nullable=False)
    category   = Column(String(100), nullable=True)     # "ai_context", "compliance", …
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id":         str(self.id),
            "org_id":     str(self.org_id),
            "key":        self.key,
            "value":      self.value,
            "category":   self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }