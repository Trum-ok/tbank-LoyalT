from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domains.applications.models import ApplicationStatus, PartnerCategory


class ApplicationCreate(BaseModel):
    business_name: str = Field(min_length=1, max_length=255)
    inn: str = Field(min_length=10, max_length=12)
    category: PartnerCategory
    contact_email: EmailStr
    contact_phone: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=2000)


class ApplicationUpdate(BaseModel):
    business_name: str | None = Field(default=None, min_length=1, max_length=255)
    inn: str | None = Field(default=None, min_length=10, max_length=12)
    category: PartnerCategory | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=2000)


class ApplicationDecision(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    business_name: str
    inn: str
    category: PartnerCategory
    contact_email: str
    contact_phone: str | None
    description: str | None
    status: ApplicationStatus
    decided_at: datetime | None
    decided_by: UUID | None
    decision_comment: str | None
    created_at: datetime
    updated_at: datetime
