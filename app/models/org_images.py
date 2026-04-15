"""
app/models/org_images.py
─────────────────────────
Models for org image management and secure review system.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class OrgImage(Base):
    __tablename__ = "org_images"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id     = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    type       = Column(String(20), nullable=False, default="gallery")
    # type: 'cover' | 'profile' | 'gallery'
    url        = Column(Text, nullable=False)
    caption    = Column(String(300), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active  = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id":         str(self.id),
            "org_id":     str(self.org_id),
            "type":       self.type,
            "url":        self.url,
            "caption":    self.caption,
            "sort_order": self.sort_order,
            "is_active":  self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ReviewToken(Base):
    __tablename__ = "review_tokens"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id     = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    email      = Column(String(320), nullable=False)
    token_hash = Column(String(128), nullable=False, unique=True, index=True)
    used_at    = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ReviewRequest(Base):
    __tablename__ = "review_requests"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id      = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    sent_by     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    email       = Column(String(320), nullable=False)
    sent_at     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    opened_at   = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "id":          str(self.id),
            "org_id":      str(self.org_id),
            "email":       self.email,
            "sent_at":     self.sent_at.isoformat() if self.sent_at else None,
            "opened_at":   self.opened_at.isoformat() if self.opened_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "status":      "reviewed" if self.reviewed_at else "opened" if self.opened_at else "sent",
        }