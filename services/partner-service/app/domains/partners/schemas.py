from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domains.applications.models import PartnerCategory
from app.domains.partners.models import PartnerStatus


class PartnerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    categories: list[PartnerCategory] | None = Field(default=None, min_length=1)
    logo_url: str | None = Field(default=None, max_length=1024)
    brand_color: str | None = Field(default=None, max_length=16)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=32)


class PartnerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    application_id: UUID
    name: str
    inn: str
    categories: list[PartnerCategory]
    logo_url: str | None
    brand_color: str | None
    contact_email: str
    contact_phone: str | None
    status: PartnerStatus
    created_at: datetime
    updated_at: datetime
