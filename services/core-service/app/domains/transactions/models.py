from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampsMixin, UUIDPKMixin


class TransactionType(StrEnum):
    ACCRUAL = "accrual"  # начисление
    REDEMPTION = "redemption"  # списание (трата на награду)
    REVERSAL = "reversal"  # отмена ранее проведённой транзакции
    EXPIRATION = "expiration"  # сгорание баллов по TTL


class Transaction(UUIDPKMixin, TimestampsMixin, Base):
    """Запись об операции с баллами.

    `points` — всегда положительное число. Направление определяется типом:
      - accrual: +points на баланс
      - redemption: -points с баланса
      - reversal: знак противоположен отменяемой транзакции
      - expiration: -points с баланса
    """

    __tablename__ = "transaction"
    __table_args__ = (
        Index("ix_transaction_customer_id", "customer_id"),
        Index("ix_transaction_program_id", "program_id"),
        Index("ix_transaction_enrollment_id", "enrollment_id"),
        Index("ix_transaction_expires_at", "expires_at"),
    )

    enrollment_id: Mapped[UUID] = mapped_column(
        ForeignKey("enrollment.id", ondelete="CASCADE")
    )
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customer.id", ondelete="CASCADE"))
    program_id: Mapped[UUID] = mapped_column(ForeignKey("program.id", ondelete="CASCADE"))
    partner_id: Mapped[UUID] = mapped_column(ForeignKey("partner.id", ondelete="CASCADE"))

    type: Mapped[TransactionType] = mapped_column(String(16))
    points: Mapped[int] = mapped_column()

    # Сумма покупки в копейках (для accrual по чеку). Опционально.
    purchase_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))

    reward_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reward.id", ondelete="SET NULL")
    )

    # Для reversal — ссылка на отменяемую транзакцию.
    reverses_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transaction.id", ondelete="SET NULL")
    )

    # Срок сгорания начисленных баллов (для accrual). None — бессрочно.
    expires_at: Mapped[datetime | None] = mapped_column()

    # Признак, что accrual-транзакция была отменена (reversal/expiration).
    is_reversed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    description: Mapped[str | None] = mapped_column(String(500))
