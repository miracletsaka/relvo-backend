from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base

class TemplateServe(Base):
    __tablename__ = "template_serves"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(String, nullable=False)
    org_id = Column(UUID(as_uuid=True), nullable=False)
    brand_id = Column(String, nullable=True)
    tone_id = Column(UUID(as_uuid=True), nullable=True)
    orientation = Column(String(10), nullable=True)
    served_at = Column(DateTime, server_default=func.now())