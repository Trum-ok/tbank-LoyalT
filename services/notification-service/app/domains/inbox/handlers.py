"""Преобразование событий в уведомления.

Каждый handler получает payload события и возвращает либо `NotificationCreate`,
либо `None`, если событие не требует push (например, у партнёра нет
подписчиков, или это служебное событие).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.notifications import service as notifications_service
from app.domains.notifications.models import NotificationType
from app.domains.notifications.schemas import NotificationCreate

logger = logging.getLogger("notification.inbox")

Handler = Callable[[AsyncSession, dict[str, Any]], Awaitable[None]]


def _format_points(points: int) -> str:
    return f"+{points} баллов" if points >= 0 else f"{points} баллов"


async def _on_points_accrued(session: AsyncSession, payload: dict[str, Any]) -> None:
    customer_id = UUID(payload["customer_id"])
    points = int(payload["points"])
    partner_name = payload.get("partner_name") or "Партнёр"
    await notifications_service.create_and_deliver(
        session,
        NotificationCreate(
            customer_id=customer_id,
            type=NotificationType.POINTS_ACCRUED,
            title=f"{_format_points(points)} · {partner_name}",
            body=f"Вам начислено {points} баллов в программе «{partner_name}».",
            payload=payload,
        ),
    )


async def _on_points_redeemed(session: AsyncSession, payload: dict[str, Any]) -> None:
    customer_id = UUID(payload["customer_id"])
    points = int(payload["points"])
    reward_title = payload.get("reward_title") or "награду"
    partner_name = payload.get("partner_name") or "Партнёр"
    await notifications_service.create_and_deliver(
        session,
        NotificationCreate(
            customer_id=customer_id,
            type=NotificationType.POINTS_REDEEMED,
            title=f"Списано {points} баллов · {partner_name}",
            body=f"Вы получили {reward_title}.",
            payload=payload,
        ),
    )


async def _on_points_expiring(session: AsyncSession, payload: dict[str, Any]) -> None:
    customer_id = UUID(payload["customer_id"])
    points = int(payload["points"])
    days_left = int(payload.get("days_left", 0))
    partner_name = payload.get("partner_name") or "Партнёр"
    await notifications_service.create_and_deliver(
        session,
        NotificationCreate(
            customer_id=customer_id,
            type=NotificationType.POINTS_EXPIRING,
            title=f"{points} баллов скоро сгорят",
            body=(
                f"У вас {points} баллов в программе «{partner_name}», "
                f"которые сгорят через {days_left} дн."
            ),
            payload=payload,
        ),
    )


async def _on_reward_available(session: AsyncSession, payload: dict[str, Any]) -> None:
    customer_id = UUID(payload["customer_id"])
    reward_title = payload.get("reward_title") or "награду"
    partner_name = payload.get("partner_name") or "Партнёр"
    await notifications_service.create_and_deliver(
        session,
        NotificationCreate(
            customer_id=customer_id,
            type=NotificationType.REWARD_AVAILABLE,
            title="Накопили на награду",
            body=f"У вас достаточно баллов в «{partner_name}», чтобы получить {reward_title}.",
            payload=payload,
        ),
    )


async def _on_new_promotion(session: AsyncSession, payload: dict[str, Any]) -> None:
    # Адресатов нет в текущем payload — это hook на будущее
    # (когда core добавит publisher для подписчиков партнёра).
    logger.info(
        "new_promotion event received but no fan-out yet: %s",
        payload.get("partner_id"),
    )


async def _on_partner_approved(session: AsyncSession, payload: dict[str, Any]) -> None:
    # Системное информационное событие. Push клиентам не нужен.
    logger.info("partner approved: %s (%s)", payload.get("name"), payload.get("inn"))


HANDLERS: dict[str, Handler] = {
    "points.accrued": _on_points_accrued,
    "points.redeemed": _on_points_redeemed,
    "points.expiring": _on_points_expiring,
    "reward.available": _on_reward_available,
    "partner.new_promotion": _on_new_promotion,
    "partner.approved": _on_partner_approved,
}


async def handle_event(
    session: AsyncSession, event_type: str, payload: dict[str, Any]
) -> bool:
    """Возвращает True, если событие было обработано (handler найден)."""
    handler = HANDLERS.get(event_type)
    if handler is None:
        logger.debug("Unknown event type: %s", event_type)
        return False
    try:
        await handler(session, payload)
    except Exception:
        logger.exception("Failed to handle event %s", event_type)
        await session.rollback()
        raise
    return True
