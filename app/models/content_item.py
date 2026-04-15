import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class ContentItem(Base):
    __tablename__ = "content_items"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id         = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=True, index=True)  # ← NEW
    brand_id       = Column(String, nullable=False)
    platform       = Column(String, nullable=False)
    topic          = Column(Text, nullable=False)
    plan_month     = Column(String(7), nullable=False)   # "YYYY-MM"
    times_per_week = Column(Integer, nullable=False)
    status         = Column(String, nullable=False, default="TOPIC_INGESTED")
    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at     = Column(DateTime, nullable=False, default=datetime.utcnow)