from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domains.programs.models import ProgramStatus, ProgramType
from app.domains.transactions.schemas import TransactionRead


class AccrueRequest(BaseModel):
    customer_id: UUID
    program_id: UUID

    # Один из вариантов начисления:
    #   purchase_amount — сумма чека (используется правило программы)
    #   points          — фиксированное число баллов
    #   visits          — для программы со штампами / визитами (по умолчанию 1)
    purchase_amount: Decimal | None = Field(default=None, ge=0)
    points: int | None = Field(default=None, ge=1)
    visits: int | None = Field(default=None, ge=1)

    description: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def check_one_of(self) -> "AccrueRequest":
        provided = [
            v is not None for v in (self.purchase_amount, self.points, self.visits)
        ]
        if sum(provided) != 1:
            raise ValueError(
                "Provide exactly one of: purchase_amount, points, visits"
            )
        return self


class RedeemRequest(BaseModel):
    customer_id: UUID
    program_id: UUID
    reward_id: UUID
    description: str | None = Field(default=None, max_length=500)


class ReverseRequest(BaseModel):
    description: str | None = Field(default=None, max_length=500)


class BalanceRead(BaseModel):
    enrollment_id: UUID
    customer_id: UUID
    program_id: UUID
    points_balance: int
    updated_at: datetime


class PointsOperationResult(BaseModel):
    transaction: TransactionRead
    balance_after: int


class RewardOption(BaseModel):
    id: UUID
    title: str
    description: str | None
    cost_points: int
    type: str


class EnrollmentLookup(BaseModel):
    """Что касса видит после сканирования QR клиента."""

    enrollment_id: UUID
    customer_id: UUID
    program_id: UUID
    program_name: str
    program_type: ProgramType
    program_status: ProgramStatus
    accrual_rule: dict[str, Any]
    min_redemption: int
    points_balance: int
    rewards: list[RewardOption]
