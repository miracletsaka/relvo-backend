from __future__ import annotations

from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BrandCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    display_name: str
    is_active: bool = True

    tones: Optional[List[str]] = []

    logo_url: Optional[str] = None
    primary_color: Optional[str] = "#7c3aed"
    secondary_color: Optional[str] = None

    tagline: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    target_audience: Optional[str] = None

    website_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    youtube_url: Optional[str] = None

    font_primary: Optional[str] = None
    font_secondary: Optional[str] = None

    brand_values: Optional[List[str]] = []


class BrandUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    display_name: Optional[str] = None
    is_active: Optional[bool] = None

    tones: Optional[List[str]] = None

    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None

    tagline: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    target_audience: Optional[str] = None

    website_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    youtube_url: Optional[str] = None

    font_primary: Optional[str] = None
    font_secondary: Optional[str] = None

    brand_values: Optional[List[str]] = None


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    is_active: bool
    org_id: UUID

    tones: Optional[List[str]] = []

    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None

    tagline: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    target_audience: Optional[str] = None

    website_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    youtube_url: Optional[str] = None

    font_primary: Optional[str] = None
    font_secondary: Optional[str] = None

    brand_values: Optional[List[str]] = []