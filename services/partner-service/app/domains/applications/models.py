from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampsMixin, UUIDPKMixin


class PartnerCategory(StrEnum):
    """Дублирует core/PartnerCategory.

    Контракт зафиксирован в событиях `partner.events`, поэтому держим
    собственное определение, а не импортируем из core.
    """

    FOOD = "food"
    BEAUTY = "beauty"
    RETAIL = "retail"
    SERVICES = "services"
    ENTERTAINMENT = "entertainment"


class ApplicationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApplicationCategory(Base):
    """Категория заявки (заявка может относиться к нескольким категориям)."""

    __tablename__ = "application_category"

    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("application.id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[str] = mapped_column(String(32), primary_key=True)


class Application(UUIDPKMixin, TimestampsMixin, Base):
    __tablename__ = "application"
    __table_args__ = (
        Index("ix_application_account_id", "account_id"),
        Index("ix_application_status", "status"),
    )

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("account.id", ondelete="CASCADE")
    )

    business_name: Mapped[str] = mapped_column(String(255))
    inn: Mapped[str] = mapped_column(String(12))
    contact_email: Mapped[str] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(String(2000))

    status: Mapped[ApplicationStatus] = mapped_column(
        String(16),
        default=ApplicationStatus.PENDING,
        server_default=ApplicationStatus.PENDING.value,
    )

    decided_at: Mapped[datetime | None] = mapped_column()
    decided_by: Mapped[UUID | None] = mapped_column()
    decision_comment: Mapped[str | None] = mapped_column(String(2000))

    category_links: Mapped[list[ApplicationCategory]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        passive_deletes=True,
        order_by="ApplicationCategory.category",
    )
    categories: AssociationProxy[list[str]] = association_proxy(
        "category_links",
        "category",
        creator=lambda c: ApplicationCategory(category=str(c)),
    )
