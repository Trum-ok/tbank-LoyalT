from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampsMixin, UUIDPKMixin


class PartnerCategory(StrEnum):
    FOOD = "food"
    BEAUTY = "beauty"
    RETAIL = "retail"
    SERVICES = "services"
    ENTERTAINMENT = "entertainment"


class PartnerStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"


class PartnerCategory_(Base):
    """Категория партнёра в снэпшоте core (партнёр может быть в нескольких).

    Имя класса с подчёркиванием — чтобы не конфликтовать с enum
    `PartnerCategory`. Таблица — `partner_category`.
    """

    __tablename__ = "partner_category"

    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("partner.id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[str] = mapped_column(String(32), primary_key=True)


class Partner(UUIDPKMixin, TimestampsMixin, Base):
    """Снэпшот партнёра в core-сервисе.

    Источник истины — partner-service; в core хранится локальная копия
    минимально необходимых полей для отображения каталога и применения
    программ лояльности.
    """

    __tablename__ = "partner"

    inn: Mapped[str] = mapped_column(String(12), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    logo_url: Mapped[str | None] = mapped_column(String(1024))
    brand_color: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[PartnerStatus] = mapped_column(
        String(16),
        default=PartnerStatus.ACTIVE,
        server_default=PartnerStatus.ACTIVE.value,
    )

    category_links: Mapped[list[PartnerCategory_]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        passive_deletes=True,
        order_by="PartnerCategory_.category",
    )
    categories: AssociationProxy[list[str]] = association_proxy(
        "category_links",
        "category",
        creator=lambda c: PartnerCategory_(category=str(c)),
    )
