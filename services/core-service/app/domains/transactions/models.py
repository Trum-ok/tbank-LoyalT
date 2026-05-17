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

    # Таблица партиционирована HASH(partner_id) (миграция 0003). Поэтому
    # PK составной — (id, partner_id): ключ секции обязан входить в каждый
    # уникальный констрейнт. `id` остаётся глобально уникальным (uuid4),
    # поэтому lookup по одному id корректен (см. transactions.service).
    __tablename__ = "transaction"
    __table_args__ = (
        Index("ix_transaction_partner_created", "partner_id", "created_at"),
        Index(
            "ix_transaction_customer_prog_created",
            "customer_id",
            "program_id",
            "created_at",
        ),
        Index("ix_transaction_enrollment_id", "enrollment_id"),
        # Частичный индекс ix_transaction_expires_at создаётся в миграции
        # (WHERE is_reversed = false AND type = 'accrual') — в metadata не
        # выражается, поэтому здесь его нет намеренно.
        # Аналогично uq_transaction_idempotency — уникальный индекс
        # (partner_id, idempotency_key) создаётся в миграции 0007. NULL в
        # unique-индексе считается различным, поэтому строки без ключа
        # (reverse/expiration) не конфликтуют (partial-unique на
        # партиционированной таблице PostgreSQL не поддерживает).
    )

    enrollment_id: Mapped[UUID] = mapped_column(
        ForeignKey("enrollment.id", ondelete="CASCADE")
    )
    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer.id", ondelete="CASCADE")
    )
    program_id: Mapped[UUID] = mapped_column(
        ForeignKey("program.id", ondelete="CASCADE")
    )
    # Часть составного PK (ключ HASH-секции).
    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("partner.id", ondelete="CASCADE"), primary_key=True
    )

    type: Mapped[TransactionType] = mapped_column(String(16))
    points: Mapped[int] = mapped_column()

    # Сумма покупки в копейках (для accrual по чеку). Опционально.
    purchase_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))

    reward_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reward.id", ondelete="SET NULL")
    )

    # Для reversal — ссылка на отменяемую транзакцию.
    # FK снят: на партиционированной таблице нельзя ссылаться на часть
    # составного PK. Целостность обеспечивает domains.points.service.reverse.
    reverses_id: Mapped[UUID | None] = mapped_column()

    # Срок сгорания начисленных баллов (для accrual). None — бессрочно.
    expires_at: Mapped[datetime | None] = mapped_column()

    # Признак, что accrual-транзакция была отменена (reversal/expiration).
    is_reversed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    # Для accrual: по этим баллам уже отправлено push-предупреждение о
    # скором сгорании — чтобы джоб не слал его повторно каждый прогон.
    expiry_warned: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    description: Mapped[str | None] = mapped_column(String(500))

    # Идемпотентность операций accrue/redeem. Ключ задаёт касса/ЛК в
    # заголовке Idempotency-Key; уникален в рамках партнёра (уникальный
    # индекс, см. миграцию 0007). request_fingerprint —
    # sha256 канонического тела запроса: повтор того же ключа с другим
    # телом → 409 (см. domains.points.service).
    idempotency_key: Mapped[str | None] = mapped_column(String(255))
    request_fingerprint: Mapped[str | None] = mapped_column(String(64))
