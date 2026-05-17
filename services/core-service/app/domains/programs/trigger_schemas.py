"""Pydantic-схемы для бонусных кампаний (BonusTrigger)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domains.programs.models import TriggerType

__all__ = [
    "TriggerType",
    "BonusTriggerCreate",
    "BonusTriggerUpdate",
    "BonusTriggerRead",
]


class BonusTriggerCreate(BaseModel):
    type: TriggerType
    name: str
    points: int
    is_active: bool = True
    days_before: int | None = None
    fire_date: date | None = None
    repeat_yearly: bool = False
    interval_days: int | None = None
    repeat_interval: bool = False


class BonusTriggerUpdate(BaseModel):
    type: TriggerType | None = None
    name: str | None = None
    points: int | None = None
    is_active: bool | None = None
    days_before: int | None = None
    fire_date: date | None = None
    repeat_yearly: bool | None = None
    interval_days: int | None = None
    repeat_interval: bool | None = None


class BonusTriggerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    type: TriggerType
    name: str
    points: int
    is_active: bool
    days_before: int | None
    fire_date: date | None
    repeat_yearly: bool
    interval_days: int | None
    repeat_interval: bool
    created_at: datetime
    updated_at: datetime
