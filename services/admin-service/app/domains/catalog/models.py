from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampsMixin, UUIDPKMixin


class CategoryOverride(TimestampsMixin, Base):
    """Переопределения для категорий каталога.

    Список кодов фиксирован в core/partner (food/beauty/...). Здесь
    хранятся только настройки отображения: порядок, описание, активность.
    """

    __tablename__ = "category_override"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(2000))
    display_order: Mapped[int] = mapped_column(default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class FeaturedPartner(UUIDPKMixin, TimestampsMixin, Base):
    """Партнёр, выделенный в «Рекомендованные»."""

    __tablename__ = "featured_partner"
    __table_args__ = (Index("ix_featured_partner_partner_id", "partner_id"),)

    # Без FK через схемы — связи между сервисами не закрепляем на уровне БД.
    partner_id: Mapped[UUID] = mapped_column(unique=True)
    position: Mapped[int] = mapped_column(default=0, server_default="0")
    starts_at: Mapped[datetime | None] = mapped_column()
    ends_at: Mapped[datetime | None] = mapped_column()


class Banner(UUIDPKMixin, TimestampsMixin, Base):
    """Промо-баннер для клиентского каталога."""

    __tablename__ = "banner"

    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(String(2000))
    image_url: Mapped[str | None] = mapped_column(String(1024))
    link_url: Mapped[str | None] = mapped_column(String(1024))
    position: Mapped[int] = mapped_column(default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    starts_at: Mapped[datetime | None] = mapped_column()
    ends_at: Mapped[datetime | None] = mapped_column()
