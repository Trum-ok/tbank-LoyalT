from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampsMixin, UUIDPKMixin


class NotificationType(StrEnum):
    POINTS_ACCRUED = "points_accrued"  # «+80 баллов · Кофе Хауз»
    POINTS_REDEEMED = "points_redeemed"  # «Списано 300 баллов · Капучино в подарок»
    POINTS_EXPIRING = "points_expiring"  # «120 баллов сгорят через 3 дня»
    REWARD_AVAILABLE = "reward_available"  # «Накопили на бесплатный кофе!»
    NEW_PROMOTION = "new_promotion"  # «Двойные баллы по средам у Кофе Хауза»
    PARTNER_APPROVED = "partner_approved"  # системное — информационное


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"  # у клиента нет активных устройств


class Notification(UUIDPKMixin, TimestampsMixin, Base):
    __tablename__ = "notification"
    __table_args__ = (
        Index("ix_notification_customer_id", "customer_id"),
        Index("ix_notification_created_at", "created_at"),
    )

    customer_id: Mapped[UUID] = mapped_column()
    type: Mapped[NotificationType] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(String(1000))
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )

    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        String(16),
        default=DeliveryStatus.PENDING,
        server_default=DeliveryStatus.PENDING.value,
    )
    delivered_at: Mapped[datetime | None] = mapped_column()
    delivery_error: Mapped[str | None] = mapped_column(String(2000))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
