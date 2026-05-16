from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminCreate(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "moderator@tbank.ru",
                    "full_name": "Иван Петров",
                }
            ]
        }
    )


class AdminUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "full_name": "Иван Петров",
                    "is_active": False,
                }
            ]
        }
    )


class AdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
