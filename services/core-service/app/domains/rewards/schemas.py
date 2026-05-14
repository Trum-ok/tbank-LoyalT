from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domains.rewards.models import RewardType


class RewardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    cost_points: int = Field(ge=1)
    type: RewardType
    value: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class RewardUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    cost_points: int | None = Field(default=None, ge=1)
    value: dict[str, Any] | None = None
    is_active: bool | None = None


class RewardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    title: str
    description: str | None
    cost_points: int
    type: RewardType
    value: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime
