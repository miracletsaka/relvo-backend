from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TemplateSegmentCreate(BaseModel):
    template_family: str
    segment_key: str

    name: str
    description: str | None = None

    shapes_json: list[dict[str, Any]]

    canvas_width: int = 1080
    canvas_height: int = 1350

    compatible_tones: list[str] = Field(default_factory=list)
    compatible_categories: list[str] = Field(default_factory=list)

    preview_url: str | None = None
    thumbnail_url: str | None = None

    generation_source: str | None = None

    tags: list[str] = Field(default_factory=list)

    is_system: bool = False


class TemplateSegmentUpdate(BaseModel):
    template_family: str | None = None
    segment_key: str | None = None

    name: str | None = None
    description: str | None = None

    shapes_json: list[dict[str, Any]] | None = None

    canvas_width: int | None = None
    canvas_height: int | None = None

    compatible_tones: list[str] | None = None
    compatible_categories: list[str] | None = None

    preview_url: str | None = None
    thumbnail_url: str | None = None

    generation_source: str | None = None

    tags: list[str] | None = None

    is_system: bool | None = None


class TemplateSegmentOut(BaseModel):
    id: UUID

    org_id: UUID

    template_family: str
    segment_key: str

    name: str
    description: str | None = None

    shapes_json: list[dict[str, Any]]

    canvas_width: int
    canvas_height: int

    compatible_tones: list[str]
    compatible_categories: list[str]

    preview_url: str | None = None
    thumbnail_url: str | None = None

    generation_source: str | None = None

    tags: list[str]

    is_system: bool

    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }