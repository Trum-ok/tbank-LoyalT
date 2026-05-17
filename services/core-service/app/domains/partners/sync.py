"""Синхронизация локального снэпшота `partner` с событиями partner-service.

partner-service публикует в топик `partner.events` сообщения вида
{type, occurred_at, payload}; payload содержит полный снэпшот партнёра.
Здесь upsert по `partner_id` и обновление статуса.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.partners.models import (
    Partner,
    PartnerCategory,
    PartnerStatus,
)

logger = logging.getLogger("core.partner_sync")


def _coerce_categories(payload: dict[str, Any]) -> list[str]:
    """Список категорий из payload.

    Поддерживает новый контракт (`categories: list`) и старый
    (`category: str`) для обратной совместимости со старыми событиями.
    Неизвестные значения отбрасываются; пустой результат → SERVICES.
    """
    raw = payload.get("categories")
    if raw is None and payload.get("category") is not None:
        raw = [payload["category"]]
    out: list[str] = []
    for value in raw or []:
        try:
            out.append(PartnerCategory(value).value)
        except ValueError:
            logger.warning("Unknown partner category from upstream: %r", value)
    return out or [PartnerCategory.SERVICES.value]


def _coerce_status(value: str | None) -> PartnerStatus:
    if value is None:
        return PartnerStatus.ACTIVE
    try:
        return PartnerStatus(value)
    except ValueError:
        logger.warning("Unknown partner status from upstream: %r", value)
        return PartnerStatus.ACTIVE


async def upsert_partner(session: AsyncSession, payload: dict[str, Any]) -> Partner:
    """Создаёт или обновляет локального партнёра по payload из partner-service.

    id в core = partner_id из partner-service — это намеренно: core не
    выдаёт свои UUID, а доверяет источнику истины.
    """
    raw_id = payload.get("partner_id")
    if not raw_id:
        raise ValueError("payload.partner_id is required")
    partner_id = UUID(str(raw_id))

    partner = await session.get(Partner, partner_id)
    if partner is None:
        partner = Partner(
            id=partner_id,
            inn=payload["inn"],
            name=payload["name"],
            categories=_coerce_categories(payload),
            logo_url=payload.get("logo_url"),
            brand_color=payload.get("brand_color"),
            status=_coerce_status(payload.get("status")),
        )
        session.add(partner)
    else:
        partner.inn = payload.get("inn", partner.inn)
        partner.name = payload.get("name", partner.name)
        if "categories" in payload or "category" in payload:
            partner.categories = _coerce_categories(payload)
        if "logo_url" in payload:
            partner.logo_url = payload["logo_url"]
        if "brand_color" in payload:
            partner.brand_color = payload["brand_color"]
        partner.status = _coerce_status(payload.get("status", partner.status))

    await session.commit()
    await session.refresh(partner)
    return partner
