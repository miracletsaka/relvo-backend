
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
 
class MediaAsset(Base):
    __tablename__ = "media_assets"
 
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url         = Column(String, nullable=False)
    filename    = Column(String, nullable=False)
    type        = Column(String, nullable=False)        # "image" | "video"
    brand_id    = Column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="SET NULL"), nullable=True, index=True)
    brand_name  = Column(String, nullable=True)        # denormalised for display
    tags        = Column(JSON, default=list)
    size_bytes  = Column(Integer, nullable=True)
    mime_type   = Column(String,  nullable=True)
    width       = Column(Integer, nullable=True)       # px — used for portrait filter
    height      = Column(Integer, nullable=True)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))