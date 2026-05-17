from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domains.programs.schemas import TierRead


class EnrollmentCreate(BaseModel):
    program_id: UUID
    display_name: str | None = Field(default=None, max_length=255)


class EnrollmentUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    is_archived: bool | None = None


class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    program_id: UUID
    short_code: str
    display_name: str | None
    is_archived: bool
    points_balance: int
    created_at: datetime
    updated_at: datetime
    current_tier: TierRead | None = None

    # Данные партнёра/программы для отображения в клиентском «Кошельке».
    # Заполняются в router._enrollment_read, в самой модели Enrollment их нет.
    partner_name: str | None = None
    partner_logo_url: str | None = None
    partner_brand_color: str | None = None
    program_name: str | None = None
