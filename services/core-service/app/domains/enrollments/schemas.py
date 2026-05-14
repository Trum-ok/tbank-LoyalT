from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    display_name: str | None
    is_archived: bool
    points_balance: int
    created_at: datetime
    updated_at: datetime
