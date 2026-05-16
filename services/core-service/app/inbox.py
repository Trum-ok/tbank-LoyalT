"""Диспетчер входящих событий из Kafka (или /internal/events).

`partner.*` — снэпшоты из partner-service; `points.*` — собственные
события core, проецируемые в read-модель аналитики (см.
domains.analytics.projection). Хендлеры коммитят сессию сами.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analytics import projection
from app.domains.partners.sync import upsert_partner

logger = logging.getLogger("core.inbox")

Handler = Callable[[AsyncSession, dict[str, Any]], Awaitable[None]]


async def _on_partner_event(session: AsyncSession, payload: dict[str, Any]) -> None:
    await upsert_partner(session, payload)


HANDLERS: dict[str, Handler] = {
    "partner.approved": _on_partner_event,
    "partner.updated": _on_partner_event,
    "partner.status_changed": _on_partner_event,
    "points.accrued": projection.apply_accrued,
    "points.redeemed": projection.apply_redeemed,
    "points.reversed": projection.apply_reversed,
}


async def handle_event(
    session: AsyncSession, event_type: str, payload: dict[str, Any]
) -> bool:
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
