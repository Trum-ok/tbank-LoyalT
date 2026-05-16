from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domains.programs.models import ProgramStatus, ProgramType


def _validate_accrual_rule(
    program_type: ProgramType, rule: dict[str, Any]
) -> dict[str, Any]:
    match program_type:
        case ProgramType.ACCRUAL:
            if "percent" not in rule and "points_per_rub" not in rule:
                raise ValueError("accrual rule requires 'percent' or 'points_per_rub'")
        case ProgramType.VISIT:
            if "points_per_visit" not in rule:
                raise ValueError("visit rule requires 'points_per_visit'")
        case ProgramType.STAMPS:
            if "visits_required" not in rule:
                raise ValueError("stamps rule requires 'visits_required'")
    return rule


class ProgramCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    type: ProgramType
    accrual_rule: dict[str, Any] = Field(default_factory=dict)
    points_ttl_days: int | None = Field(default=None, ge=1, le=3650)
    min_redemption: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def check_rule(self) -> "ProgramCreate":
        _validate_accrual_rule(self.type, self.accrual_rule)
        return self


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    accrual_rule: dict[str, Any] | None = None
    points_ttl_days: int | None = Field(default=None, ge=1, le=3650)
    min_redemption: int | None = Field(default=None, ge=0)


class ProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    partner_id: UUID
    name: str
    description: str | None
    type: ProgramType
    accrual_rule: dict[str, Any]
    points_ttl_days: int | None
    min_redemption: int
    status: ProgramStatus
    created_at: datetime
    updated_at: datetime
