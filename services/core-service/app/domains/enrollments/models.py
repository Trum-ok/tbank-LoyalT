from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampsMixin, UUIDPKMixin


class Customer(UUIDPKMixin, TimestampsMixin, Base):
    """Профиль клиента.

    Идентификатор соответствует T-ID. В core хранится только то, что
    нужно для работы с программами; персональные данные — в банке.
    """

    __tablename__ = "customer"


class Enrollment(UUIDPKMixin, TimestampsMixin, Base):
    """Подключение клиента к программе лояльности."""

    __tablename__ = "enrollment"
    __table_args__ = (
        UniqueConstraint("customer_id", "program_id", name="uq_enrollment_customer_program"),
        Index("ix_enrollment_customer_id", "customer_id"),
        Index("ix_enrollment_program_id", "program_id"),
    )

    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customer.id", ondelete="CASCADE"))
    program_id: Mapped[UUID] = mapped_column(ForeignKey("program.id", ondelete="CASCADE"))
    display_name: Mapped[str | None] = mapped_column(String(255))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Денормализованный баланс. Обновляется атомарно при каждой транзакции
    # в одной транзакции БД (см. domains.points.service).
    points_balance: Mapped[int] = mapped_column(default=0, server_default="0")
