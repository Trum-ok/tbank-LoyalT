"""Логика создания и доставки уведомлений.

Доставка stub-овая: сохраняем запись в БД и логируем "отправку" каждому
активному устройству. Когда подключим реальный провайдер (FCM/APNs),
заменим тело `_deliver` — публичный контракт `create_and_deliver` останется
прежним.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.devices.service import list_active_for_customer
from app.domains.notifications.models import (
    DeliveryStatus,
    Notification,
)
from app.domains.notifications.schemas import NotificationCreate
from app.errors import ForbiddenError, NotFoundError

logger = logging.getLogger("notification.delivery")


async def create_and_deliver(
    session: AsyncSession, data: NotificationCreate
) -> Notification:
    notification = Notification(
        customer_id=data.customer_id,
        type=data.type,
        title=data.title,
        body=data.body,
        payload=data.payload,
    )
    session.add(notification)
    await session.flush()

    await _deliver(session, notification)
    await session.commit()
    await session.refresh(notification)
    return notification


async def _deliver(session: AsyncSession, notification: Notification) -> None:
    devices = await list_active_for_customer(session, notification.customer_id)
    if not devices:
        notification.delivery_status = DeliveryStatus.SKIPPED
        notification.delivery_error = "No active devices"
        logger.info(
            "push(skip) customer=%s type=%s — no active devices",
            notification.customer_id,
            notification.type,
        )
        return

    for device in devices:
        logger.info(
            "push(stub) device=%s platform=%s token=%s title=%r",
            device.id,
            device.platform,
            device.token[:12] + "…",
            notification.title,
        )
    notification.delivery_status = DeliveryStatus.SENT
    notification.delivered_at = datetime.now(UTC)


async def list_for_customer(
    session: AsyncSession,
    customer_id: UUID,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Notification]:
    stmt = select(Notification).where(Notification.customer_id == customer_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def mark_read(
    session: AsyncSession, customer_id: UUID, notification_id: UUID
) -> Notification:
    notification = await session.get(Notification, notification_id)
    if notification is None:
        raise NotFoundError("Notification not found")
    if notification.customer_id != customer_id:
        raise ForbiddenError("Notification belongs to another customer")
    notification.is_read = True
    await session.commit()
    await session.refresh(notification)
    return notification
