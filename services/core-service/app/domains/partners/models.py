from enum import StrEnum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

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


class Partner(UUIDPKMixin, TimestampsMixin, Base):
    """Снэпшот партнёра в core-сервисе.

    Источник истины — partner-service; в core хранится локальная копия
    минимально необходимых полей для отображения каталога и применения
    программ лояльности.
    """

    __tablename__ = "partner"

    inn: Mapped[str] = mapped_column(String(12), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[PartnerCategory] = mapped_column(String(32))
    logo_url: Mapped[str | None] = mapped_column(String(1024))
    brand_color: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[PartnerStatus] = mapped_column(
        String(16),
        default=PartnerStatus.ACTIVE,
        server_default=PartnerStatus.ACTIVE.value,
    )
