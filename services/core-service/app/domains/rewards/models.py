from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampsMixin, UUIDPKMixin


class RewardType(StrEnum):
    DISCOUNT_PERCENT = "discount_percent"
    DISCOUNT_FIXED = "discount_fixed"
    FREE_ITEM = "free_item"
    CASHBACK_BOOST = "cashback_boost"


class Reward(UUIDPKMixin, TimestampsMixin, Base):
    __tablename__ = "reward"
    __table_args__ = (Index("ix_reward_program_id", "program_id"),)

    program_id: Mapped[UUID] = mapped_column(ForeignKey("program.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(2000))
    cost_points: Mapped[int] = mapped_column()
    type: Mapped[RewardType] = mapped_column(String(32))

    # Содержимое value зависит от type:
    #   discount_percent: {"percent": 10}
    #   discount_fixed:   {"amount": 200, "currency": "RUB"}
    #   free_item:        {"item": "Капучино 250 мл"}
    #   cashback_boost:   {"multiplier": 2, "days": 7}
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
