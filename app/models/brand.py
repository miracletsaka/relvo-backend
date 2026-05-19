from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func

from app.database import Base


class Brand(Base):
    __tablename__ = "brands"

    id = Column(String(100), primary_key=True)

    display_name = Column(String(200), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    org_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)

    tones = Column(ARRAY(Text), nullable=True, default=[])

    logo_url = Column(Text, nullable=True)
    primary_color = Column(String(20), nullable=True, default="#7c3aed")
    secondary_color = Column(String(20), nullable=True)

    tagline = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    industry = Column(String(120), nullable=True)
    target_audience = Column(Text, nullable=True)

    website_url = Column(Text, nullable=True)
    email = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    address = Column(Text, nullable=True)

    facebook_url = Column(Text, nullable=True)
    instagram_url = Column(Text, nullable=True)
    linkedin_url = Column(Text, nullable=True)
    twitter_url = Column(Text, nullable=True)
    tiktok_url = Column(Text, nullable=True)
    youtube_url = Column(Text, nullable=True)

    font_primary = Column(String(120), nullable=True)
    font_secondary = Column(String(120), nullable=True)

    brand_values = Column(ARRAY(Text), nullable=True, default=[])