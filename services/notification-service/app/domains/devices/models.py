from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampsMixin, UUIDPKMixin


class DevicePlatform(StrEnum):
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


class Device(UUIDPKMixin, TimestampsMixin, Base):
    """Зарегистрированный device token клиента для push-доставки."""

    __tablename__ = "device"
    __table_args__ = (
        UniqueConstraint("customer_id", "token", name="uq_device_customer_token"),
        Index("ix_device_customer_id", "customer_id"),
    )

    customer_id: Mapped[UUID] = mapped_column()
    token: Mapped[str] = mapped_column(String(512))
    platform: Mapped[DevicePlatform] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
