from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampsMixin, UUIDPKMixin


class ProgramType(StrEnum):
    """Шаблоны программ лояльности."""

    ACCRUAL = "accrual"  # Накопительная (баллы за каждые N рублей / % от чека)
    VISIT = "visit"  # Фиксированные баллы за визит
    STAMPS = "stamps"  # X визитов → награда


class ProgramStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    PAUSED = "paused"
    ARCHIVED = "archived"


class Program(UUIDPKMixin, TimestampsMixin, Base):
    __tablename__ = "program"
    __table_args__ = (
        Index("ix_program_partner_id", "partner_id"),
        Index("ix_program_status", "status"),
    )

    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("partner.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(2000))
    type: Mapped[ProgramType] = mapped_column(String(16))

    # Правила начисления — структура зависит от типа:
    #   accrual: {"percent": 5}                          5% от чека
    #   accrual: {"points_per_rub": 0.05}                эквивалент
    #   visit:   {"points_per_visit": 50}
    #   stamps:  {"visits_required": 8}
    accrual_rule: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    points_ttl_days: Mapped[int | None] = mapped_column()
    min_redemption: Mapped[int] = mapped_column(default=0, server_default="0")

    status: Mapped[ProgramStatus] = mapped_column(
        String(16),
        default=ProgramStatus.DRAFT,
        server_default=ProgramStatus.DRAFT.value,
    )
