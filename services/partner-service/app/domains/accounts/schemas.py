from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AccountCreate(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "owner@coffee-point.ru",
                    "full_name": "Иван Петров",
                    "phone": "+79001234567",
                }
            ]
        }
    }


class AccountUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    phone: str | None
    created_at: datetime
    updated_at: datetime
