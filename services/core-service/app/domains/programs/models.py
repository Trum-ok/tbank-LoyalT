from datetime import date
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import Date, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    # --- Бонусные механики ---
    # Начисляются единожды при первом вступлении клиента в программу
    welcome_bonus_points: Mapped[int | None] = mapped_column(Integer)
    # Баллы в день рождения; birthday_bonus_days — за сколько дней до ДР начислять
    birthday_bonus_points: Mapped[int | None] = mapped_column(Integer)
    birthday_bonus_days: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    # Баллы тому, кто пригласил нового клиента в программу
    referral_bonus_points: Mapped[int | None] = mapped_column(Integer)

    # --- Ограничения начисления ---
    # Минимальная сумма покупки в копейках для начисления баллов
    min_purchase_amount: Mapped[int | None] = mapped_column(Integer)
    # Максимум баллов, которые можно начислить за одну транзакцию
    max_points_per_transaction: Mapped[int | None] = mapped_column(Integer)

    # --- Ограничения списания ---
    # Максимальный % суммы покупки, который клиент может погасить баллами (1–100)
    max_redemption_percent: Mapped[int | None] = mapped_column(Integer)

    # --- Период действия программы ---
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)

    tiers: Mapped[list["ProgramTier"]] = relationship(
        "ProgramTier",
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="ProgramTier.threshold_points",
    )


class ProgramTier(UUIDPKMixin, Base):
    """Уровень лояльности внутри программы (Бронза / Серебро / Золото и т.д.)."""

    __tablename__ = "program_tier"
    __table_args__ = (
        Index("ix_program_tier_program_id", "program_id"),
        UniqueConstraint("program_id", "name", name="uq_program_tier_name"),
        UniqueConstraint(
            "program_id", "threshold_points", name="uq_program_tier_threshold"
        ),
    )

    program_id: Mapped[UUID] = mapped_column(
        ForeignKey("program.id", ondelete="CASCADE")
    )
    # Отображаемое название уровня, например «Бронзовый», «Серебряный»
    name: Mapped[str] = mapped_column(String(100))
    # Накопленные баллы за всё время, необходимые для входа в уровень
    threshold_points: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    # Множитель начисления относительно базового правила (1.0 = без изменений)
    accrual_multiplier: Mapped[float] = mapped_column(
        Float, default=1.0, server_default="1.0"
    )

    program: Mapped["Program"] = relationship("Program", back_populates="tiers")
