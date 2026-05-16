"""Клиент core-service для резолва аудитории рассылок.

Синхронный REST по внутренней сети (см. CLAUDE.md: сервис→сервис синхронно
через REST допустимо). PII в core нет — возвращаются только UUID клиентов.
"""

from __future__ import annotations

from uuid import UUID

import httpx

from app.config import get_settings
from app.errors import BadRequestError

settings = get_settings()


async def resolve_audience(
    partner_id: UUID,
    segment: str,
    program_id: UUID | None = None,
) -> list[UUID]:
    params: dict[str, str] = {
        "partner_id": str(partner_id),
        "segment": segment,
    }
    if program_id is not None:
        params["program_id"] = str(program_id)

    url = f"{settings.core_base_url.rstrip('/')}/internal/partner-audience"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise BadRequestError(
            f"Не удалось получить аудиторию из core-service: {exc}"
        ) from exc

    data = resp.json()
    return [UUID(str(cid)) for cid in data.get("customer_ids", [])]
