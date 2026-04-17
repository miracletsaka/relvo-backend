from datetime import datetime
from uuid import UUID as PyUUID

from sqlalchemy import String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, ARRAY

from app.database import Base


class Brand(Base):
    __tablename__ = "brands"
 
    id            = Column(String(100), primary_key=True)
    display_name  = Column(String(200), nullable=False)
    is_active     = Column(Boolean, default=True, nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    org_id        = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    tones         = Column(ARRAY(Text), default=list, nullable=True)
    logo_url      = Column(Text, nullable=True)
    primary_color = Column(String(20), nullable=True, default="#7c3aed")
 
    def to_dict(self):
        return {
            "id":            self.id,
            "display_name":  self.display_name,
            "is_active":     self.is_active,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
            "org_id":        str(self.org_id),
            "tones":         self.tones or [],
            "logo_url":      self.logo_url,
            "primary_color": self.primary_color,
        }
 