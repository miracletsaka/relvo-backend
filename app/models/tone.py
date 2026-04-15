from __future__ import annotations

import uuid
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Tone(Base):
    __tablename__ = "tones"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(100), nullable=False, unique=True, index=True)
    label       = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    emoji       = Column(String(10), nullable=True)
    is_active   = Column(Boolean, default=True, nullable=False)
    sort_order  = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "emoji": self.emoji,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BrandTone(Base):
    __tablename__ = "brand_tones"

    brand_id = Column(String(100), ForeignKey("brands.id", ondelete="CASCADE"), primary_key=True)
    tone_id  = Column(UUID(as_uuid=True), ForeignKey("tones.id", ondelete="CASCADE"), primary_key=True)