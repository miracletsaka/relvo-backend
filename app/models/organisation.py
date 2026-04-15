"""
app/models/organisation.py
──────────────────────────
Organisation (tenant) and membership models.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


# ── Plan limits (used when org.max_* is None) ─────────────────────────────────

PLAN_LIMITS = {
    "free": {
        "max_brands":     1,
        "max_platforms":  2,
        "max_drafts_pm":  20,
        "max_renders_pm": 0,
    },
    "starter": {
        "max_brands":     3,
        "max_platforms":  5,
        "max_drafts_pm":  200,
        "max_renders_pm": 10,
    },
    "pro": {
        "max_brands":     10,
        "max_platforms":  999,
        "max_drafts_pm":  999999,
        "max_renders_pm": 999999,
    },
    "agency": {
        "max_brands":     999999,
        "max_platforms":  999999,
        "max_drafts_pm":  999999,
        "max_renders_pm": 999999,
    },
}


class Organisation(Base):
    __tablename__ = "organisations"

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name    = Column(String(255), nullable=False)
    slug    = Column(String(100), nullable=False, unique=True)
    plan    = Column(String(50),  nullable=False, default="free")

    # Stripe
    stripe_customer_id     = Column(String(100), unique=True, nullable=True)
    stripe_subscription_id = Column(String(100), unique=True, nullable=True)
    plan_expires_at        = Column(DateTime(timezone=True), nullable=True)

    # Custom overrides (NULL = use PLAN_LIMITS defaults)
    max_brands     = Column(Integer, nullable=True)
    max_platforms  = Column(Integer, nullable=True)
    max_drafts_pm  = Column(Integer, nullable=True)
    max_renders_pm = Column(Integer, nullable=True)

    is_active  = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    members = relationship("OrganisationMember", back_populates="organisation",
                           cascade="all, delete-orphan")

    def get_limit(self, key: str) -> int:
        """Return effective limit — org override takes priority over plan default."""
        custom = getattr(self, key, None)
        if custom is not None:
            return custom
        return PLAN_LIMITS.get(self.plan, PLAN_LIMITS["free"]).get(key, 0)

    def to_dict(self) -> dict:
        return {
            "id":      str(self.id),
            "name":    self.name,
            "slug":    self.slug,
            "plan":    self.plan,
            "limits": {
                "max_brands":     self.get_limit("max_brands"),
                "max_platforms":  self.get_limit("max_platforms"),
                "max_drafts_pm":  self.get_limit("max_drafts_pm"),
                "max_renders_pm": self.get_limit("max_renders_pm"),
            },
            "is_active":  self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class OrganisationMember(Base):
    __tablename__ = "organisation_members"
    __table_args__ = (UniqueConstraint("org_id", "user_id"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id      = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id",         ondelete="CASCADE"), nullable=False)
    role        = Column(String(20), nullable=False, default="member")
    # role: owner | admin | member | viewer
    invited_by  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    joined_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    organisation = relationship("Organisation", back_populates="members")

    def to_dict(self) -> dict:
        return {
            "id":       str(self.id),
            "org_id":   str(self.org_id),
            "user_id":  str(self.user_id),
            "role":     self.role,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
        }


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id   = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    user_id  = Column(UUID(as_uuid=True), ForeignKey("users.id",         ondelete="SET NULL"), nullable=True)
    action   = Column(String(50), nullable=False)
    # action: draft_generated | video_rendered | image_generated | brand_created
    quantity = Column(Integer, nullable=False, default=1)
    period   = Column(String(7), nullable=False)  # "2026-03"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))