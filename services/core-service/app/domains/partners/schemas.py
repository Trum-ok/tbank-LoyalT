from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domains.partners.models import PartnerCategory, PartnerStatus


class PartnerCreate(BaseModel):
    inn: str = Field(min_length=10, max_length=12)
    name: str = Field(min_length=1, max_length=255)
    category: PartnerCategory
    logo_url: str | None = None
    brand_color: str | None = Field(default=None, max_length=16)


class PartnerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: PartnerCategory | None = None
    logo_url: str | None = None
    brand_color: str | None = Field(default=None, max_length=16)
    status: PartnerStatus | None = None


class PartnerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inn: str
    name: str
    category: PartnerCategory
    logo_url: str | None
    brand_color: str | None
    status: PartnerStatus
    created_at: datetime
    updated_at: datetime
