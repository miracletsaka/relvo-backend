from pydantic import BaseModel
from typing import Optional

class BrandCreate(BaseModel):
    id: str
    display_name: str
    is_active: bool = True
    logo_url:      Optional[str]  = None
    primary_color: Optional[str]  = None

class BrandUpdate(BaseModel):
    display_name: str | None = None
    is_active: bool | None = None
    logo_url:      Optional[str]  = None
    primary_color: Optional[str]  = None


class BrandOut(BaseModel):
    id: str
    display_name: str
    is_active: bool
    logo_url:      Optional[str]  = None
    primary_color: Optional[str]  = None

    class Config:
        from_attributes = True
