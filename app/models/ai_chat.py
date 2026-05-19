from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.database import Base

class AiChatThread(Base):
    __tablename__ = "ai_chat_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_id = Column(String(100), ForeignKey("brands.id", ondelete="SET NULL"), nullable=True, index=True)
    tone_id = Column(UUID(as_uuid=True), ForeignKey("tones.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(Text, nullable=False, default="New chat")
    status = Column(String(40), nullable=False, default="active")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class AiChatMessage(Base):
    __tablename__ = "ai_chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    thread_id = Column(UUID(as_uuid=True), ForeignKey("ai_chat_threads.id", ondelete="CASCADE"), nullable=False, index=True)

    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)

    role = Column(String(30), nullable=False)
    content = Column(Text, nullable=False)

    message_type = Column(String(40), nullable=False, default="text")

    meta_json = Column(
    JSONB,
    nullable=False,
    default=dict,
    server_default="{}",
)

    draft_id = Column(UUID(as_uuid=True), ForeignKey("content_drafts.id", ondelete="SET NULL"), nullable=True)

    canvas_state_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
