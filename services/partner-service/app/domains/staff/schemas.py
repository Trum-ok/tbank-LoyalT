from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

LoginCode = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
Pin = Field(min_length=4, max_length=8, pattern=r"^\d+$")


class StaffCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    login_code: str = LoginCode
    pin: str = Pin

    @field_validator("login_code")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.upper()


class StaffUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    pin: str | None = Field(default=None, min_length=4, max_length=8, pattern=r"^\d+$")
    is_active: bool | None = None


class StaffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    partner_id: UUID
    name: str
    login_code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StaffLoginRequest(BaseModel):
    login_code: str = LoginCode
    pin: str = Pin

    @field_validator("login_code")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.upper()


class StaffLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    staff_id: UUID
    staff_name: str
    partner_id: UUID
    partner_name: str
