from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domains.programs.models import ProgramStatus, ProgramType


def _validate_accrual_rule(program_type: ProgramType, rule: dict[str, Any]) -> dict[str, Any]:
    match program_type:
        case ProgramType.ACCRUAL:
            if "percent" not in rule and "points_per_rub" not in rule:
                raise ValueError(
                    "accrual rule requires 'percent' or 'points_per_rub'"
                )
        case ProgramType.VISIT:
            if "points_per_visit" not in rule:
                raise ValueError("visit rule requires 'points_per_visit'")
        case ProgramType.STAMPS:
            if "visits_required" not in rule:
                raise ValueError("stamps rule requires 'visits_required'")
    return rule


def _validate_expire_warn(ttl_days: int | None, warn_days: int | None) -> None:
    """Предупреждение о сгорании имеет смысл только при конечном TTL и
    должно срабатывать раньше самого сгорания."""
    if warn_days is None:
        return
    if ttl_days is None:
        raise ValueError(
            "expire_warn_days requires points_ttl_days to be set"
        )
    if warn_days >= ttl_days:
        raise ValueError("expire_warn_days must be smaller than points_ttl_days")


class ProgramCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    type: ProgramType
    accrual_rule: dict[str, Any] = Field(default_factory=dict)
    points_ttl_days: int | None = Field(default=None, ge=1, le=3650)
    expire_warn_days: int | None = Field(default=None, ge=1, le=365)
    min_redemption: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def check_rule(self) -> "ProgramCreate":
        _validate_accrual_rule(self.type, self.accrual_rule)
        _validate_expire_warn(self.points_ttl_days, self.expire_warn_days)
        return self


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    accrual_rule: dict[str, Any] | None = None
    points_ttl_days: int | None = Field(default=None, ge=1, le=3650)
    expire_warn_days: int | None = Field(default=None, ge=1, le=365)
    min_redemption: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def check_warn(self) -> "ProgramUpdate":
        # Кросс-валидация возможна, только если оба поля пришли в патче;
        # частичное обновление одного поля проверяется на уровне сервиса
        # против актуального состояния программы.
        fields = self.model_fields_set
        if "expire_warn_days" in fields and "points_ttl_days" in fields:
            _validate_expire_warn(self.points_ttl_days, self.expire_warn_days)
        return self


class ProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    partner_id: UUID
    name: str
    description: str | None
    type: ProgramType
    accrual_rule: dict[str, Any]
    points_ttl_days: int | None
    expire_warn_days: int | None
    min_redemption: int
    status: ProgramStatus
    created_at: datetime
    updated_at: datetime
