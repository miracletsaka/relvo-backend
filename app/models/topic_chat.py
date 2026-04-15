import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSON, UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base


class TopicChat(Base):
    __tablename__ = "topic_chats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tone_id = Column(UUID(as_uuid=True), ForeignKey("tones.id", ondelete="SET NULL"), nullable=True, index=True)

    brand_id = Column(
        String,
        nullable=False,
        index=True,
    )

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    topic = Column(Text, nullable=False)

    generation_status = Column(String, default="processing", nullable=True)
    generation_result = Column(JSON, nullable=True)
    generation_error = Column(String, nullable=True)

    background_images = Column(JSONB, nullable=False, server_default="[]")

    target_month = Column(String(7), nullable=True)   # "YYYY-MM"
    posts_per_week = Column(Integer, nullable=True)

    timezone = Column(String, nullable=False, default="Europe/London")
    posting_hour_local = Column(Integer, nullable=False, default=9)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())