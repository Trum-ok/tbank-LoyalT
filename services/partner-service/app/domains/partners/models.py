from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampsMixin, UUIDPKMixin
from app.domains.applications.models import PartnerCategory


class PartnerStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"  # временно приостановлен (партнёр сам или Т-банк)
    BLOCKED = "blocked"  # заблокирован Т-банком


class Partner(UUIDPKMixin, TimestampsMixin, Base):
    """Одобренный бизнес-партнёр.

    `account_id` — владелец ЛК. На текущем этапе одна компания = один аккаунт;
    мульти-аккаунт добавим, когда понадобится.
    """

    __tablename__ = "partner"

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE"), unique=True
    )
    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("application.id", ondelete="SET NULL"), unique=True
    )

    name: Mapped[str] = mapped_column(String(255))
    inn: Mapped[str] = mapped_column(String(12), unique=True)
    category: Mapped[PartnerCategory] = mapped_column(String(32))

    logo_url: Mapped[str | None] = mapped_column(String(1024))
    brand_color: Mapped[str | None] = mapped_column(String(16))

    contact_email: Mapped[str] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(32))

    status: Mapped[PartnerStatus] = mapped_column(
        String(16), default=PartnerStatus.ACTIVE, server_default=PartnerStatus.ACTIVE.value
    )
