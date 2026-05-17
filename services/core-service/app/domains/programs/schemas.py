from datetime import date, datetime
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


# ---------------------------------------------------------------------------
# Tier schemas
# ---------------------------------------------------------------------------


class TierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    threshold_points: int = Field(default=0, ge=0)
    accrual_multiplier: float = Field(default=1.0, ge=0.1, le=10.0)


class TierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    threshold_points: int | None = Field(default=None, ge=0)
    accrual_multiplier: float | None = Field(default=None, ge=0.1, le=10.0)


class TierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    name: str
    threshold_points: int
    accrual_multiplier: float


# ---------------------------------------------------------------------------
# Program schemas
# ---------------------------------------------------------------------------


class ProgramCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    type: ProgramType
    accrual_rule: dict[str, Any] = Field(default_factory=dict)
    points_ttl_days: int | None = Field(default=None, ge=1, le=3650)
    expire_warn_days: int | None = Field(default=None, ge=1, le=365)
    min_redemption: int = Field(default=0, ge=0)

    # Бонусные механики
    welcome_bonus_points: int | None = Field(default=None, ge=1)
    birthday_bonus_points: int | None = Field(default=None, ge=1)
    birthday_bonus_days: int = Field(default=0, ge=0, le=30)
    referral_bonus_points: int | None = Field(default=None, ge=1)

    # Ограничения начисления
    min_purchase_amount: int | None = Field(
        default=None, ge=1, description="Минимальная сумма покупки в копейках"
    )
    max_points_per_transaction: int | None = Field(default=None, ge=1)

    # Ограничения списания
    max_redemption_percent: int | None = Field(default=None, ge=1, le=100)

    # Период действия
    valid_from: date | None = None
    valid_until: date | None = None

    @model_validator(mode="after")
    def check_rule(self) -> "ProgramCreate":
        _validate_accrual_rule(self.type, self.accrual_rule)
        _validate_expire_warn(self.points_ttl_days, self.expire_warn_days)
        return self

    @model_validator(mode="after")
    def check_dates(self) -> "ProgramCreate":
        if self.valid_from and self.valid_until and self.valid_from > self.valid_until:
            raise ValueError("valid_from must be before valid_until")
        return self


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    accrual_rule: dict[str, Any] | None = None
    points_ttl_days: int | None = Field(default=None, ge=1, le=3650)
    expire_warn_days: int | None = Field(default=None, ge=1, le=365)
    min_redemption: int | None = Field(default=None, ge=0)

    # Бонусные механики
    welcome_bonus_points: int | None = Field(default=None, ge=1)
    birthday_bonus_points: int | None = Field(default=None, ge=1)
    birthday_bonus_days: int | None = Field(default=None, ge=0, le=30)
    referral_bonus_points: int | None = Field(default=None, ge=1)

    # Ограничения начисления
    min_purchase_amount: int | None = Field(default=None, ge=1)
    max_points_per_transaction: int | None = Field(default=None, ge=1)

    # Ограничения списания
    max_redemption_percent: int | None = Field(default=None, ge=1, le=100)

    # Период действия
    valid_from: date | None = None
    valid_until: date | None = None

    @model_validator(mode="after")
    def check_warn(self) -> "ProgramUpdate":
        # Кросс-валидация возможна, только если оба поля пришли в патче;
        # частичное обновление одного поля проверяется на уровне сервиса
        # против актуального состояния программы.
        fields = self.model_fields_set
        if "expire_warn_days" in fields and "points_ttl_days" in fields:
            _validate_expire_warn(self.points_ttl_days, self.expire_warn_days)
        return self

    @model_validator(mode="after")
    def check_dates(self) -> "ProgramUpdate":
        if self.valid_from and self.valid_until and self.valid_from > self.valid_until:
            raise ValueError("valid_from must be before valid_until")
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

    # Бонусные механики
    welcome_bonus_points: int | None
    birthday_bonus_points: int | None
    birthday_bonus_days: int
    referral_bonus_points: int | None

    # Ограничения начисления
    min_purchase_amount: int | None
    max_points_per_transaction: int | None

    # Ограничения списания
    max_redemption_percent: int | None

    # Период действия
    valid_from: date | None
    valid_until: date | None

    tiers: list[TierRead] = []
