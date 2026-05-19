from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func

from app.database import Base


class TemplateSegment(Base):
    __tablename__ = "template_segments"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
    )

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    template_family = Column(
        String(100),
        nullable=False,
        index=True,
    )

    segment_key = Column(
        String(100),
        nullable=False,
        index=True,
    )

    name = Column(
        String(200),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    shapes_json = Column(
        JSONB,
        nullable=False,
    )

    canvas_width = Column(
        Integer,
        nullable=False,
        default=1080,
    )

    canvas_height = Column(
        Integer,
        nullable=False,
        default=1350,
    )

    compatible_tones = Column(
        ARRAY(Text),
        nullable=False,
        default=list,
    )

    compatible_categories = Column(
        ARRAY(Text),
        nullable=False,
        default=list,
    )

    preview_url = Column(
        Text,
        nullable=True,
    )

    thumbnail_url = Column(
        Text,
        nullable=True,
    )

    generation_source = Column(
        String(100),
        nullable=True,
    )

    tags = Column(
        ARRAY(Text),
        nullable=False,
        default=list,
    )

    is_system = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )