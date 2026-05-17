from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CategoryUpsert(BaseModel):
    label: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    display_order: int = Field(default=0, ge=0)
    is_active: bool = True


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    label: str
    description: str | None
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class FeaturedPartnerCreate(BaseModel):
    partner_id: UUID
    position: int = Field(default=0, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "partner_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "position": 1,
                    "starts_at": "2026-05-17T00:00:00Z",
                    "ends_at": "2026-06-17T00:00:00Z",
                }
            ]
        }
    )


class FeaturedPartnerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    partner_id: UUID
    position: int
    starts_at: datetime | None
    ends_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BannerCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str | None = Field(default=None, max_length=2000)
    image_url: str | None = Field(default=None, max_length=1024)
    link_url: str | None = Field(default=None, max_length=1024)
    position: int = Field(default=0, ge=0)
    is_active: bool = True
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class BannerUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, max_length=2000)
    image_url: str | None = Field(default=None, max_length=1024)
    link_url: str | None = Field(default=None, max_length=1024)
    position: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class BannerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    body: str | None
    image_url: str | None
    link_url: str | None
    position: int
    is_active: bool
    starts_at: datetime | None
    ends_at: datetime | None
    created_at: datetime
    updated_at: datetime
