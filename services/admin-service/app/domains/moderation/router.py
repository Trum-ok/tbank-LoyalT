"""Прокси-роуты модерации поверх partner-service.

Бизнес-логика остаётся в partner-service. Здесь только:
  - проверка, что вызывающий — активный admin
  - переброс запроса с правильным заголовком
  - перенос ошибок upstream как 502.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from loyalt_common import error_responses

from app.clients.partner import partner_client
from app.deps import CurrentAdmin
from app.domains.moderation.schemas import DecisionRequest

applications_router = APIRouter(prefix="/moderation/applications", tags=["moderation"])
partners_router = APIRouter(prefix="/moderation/partners", tags=["moderation"])


@applications_router.get(
    "",
    summary="Список заявок партнёров",
    responses=error_responses(401, 403),
)
async def list_applications(
    admin: CurrentAdmin,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    """Заявки на подключение партнёров (прокси к partner-service).
    Фильтр `status` опционален. 401/403 — проблема с авторизацией админа.
    """
    return await partner_client.list_applications(
        admin.id, status_filter=status_filter, limit=limit, offset=offset
    )


@applications_router.get(
    "/{application_id}",
    summary="Карточка заявки",
    responses=error_responses(401, 403),
)
async def get_application(application_id: UUID, admin: CurrentAdmin) -> dict[str, Any]:
    """Детали одной заявки (прокси к partner-service). 401/403 — проблема
    с авторизацией админа."""
    return await partner_client.get_application(admin.id, application_id)


@applications_router.post(
    "/{application_id}/approve",
    summary="Одобрить заявку",
    responses=error_responses(401, 403),
)
async def approve_application(
    application_id: UUID,
    data: DecisionRequest,
    admin: CurrentAdmin,
) -> dict[str, Any]:
    """Одобряет заявку партнёра с необязательным комментарием
    модератора. Решение применяет partner-service. 401/403 — проблема с
    авторизацией админа.
    """
    return await partner_client.approve_application(
        admin.id, application_id, data.comment
    )


@applications_router.post(
    "/{application_id}/reject",
    summary="Отклонить заявку",
    responses=error_responses(401, 403),
)
async def reject_application(
    application_id: UUID,
    data: DecisionRequest,
    admin: CurrentAdmin,
) -> dict[str, Any]:
    """Отклоняет заявку партнёра с необязательной причиной отказа.
    Решение применяет partner-service. 401/403 — проблема с авторизацией
    админа.
    """
    return await partner_client.reject_application(
        admin.id, application_id, data.comment
    )


@partners_router.get(
    "",
    summary="Список партнёров",
    responses=error_responses(401, 403),
)
async def list_partners(
    admin: CurrentAdmin,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    """Партнёры платформы с фильтром по статусу (прокси к
    partner-service). 401/403 — проблема с авторизацией админа."""
    return await partner_client.list_partners(
        admin.id, status_filter=status_filter, limit=limit, offset=offset
    )


@partners_router.get(
    "/{partner_id}",
    summary="Карточка партнёра",
    responses=error_responses(401, 403),
)
async def get_partner(partner_id: UUID, admin: CurrentAdmin) -> dict[str, Any]:
    """Детали одного партнёра (прокси к partner-service). 401/403 —
    проблема с авторизацией админа."""
    return await partner_client.get_partner(admin.id, partner_id)


@partners_router.post(
    "/{partner_id}/suspend",
    summary="Приостановить партнёра",
    responses=error_responses(401, 403),
)
async def suspend_partner(partner_id: UUID, admin: CurrentAdmin) -> dict[str, Any]:
    """Временно приостанавливает партнёра. Статус меняет partner-service.
    401/403 — проблема с авторизацией админа."""
    return await partner_client.suspend_partner(admin.id, partner_id)


@partners_router.post(
    "/{partner_id}/block",
    summary="Заблокировать партнёра",
    responses=error_responses(401, 403),
)
async def block_partner(partner_id: UUID, admin: CurrentAdmin) -> dict[str, Any]:
    """Блокирует партнёра (программы перестают работать). Статус меняет
    partner-service. 401/403 — проблема с авторизацией админа."""
    return await partner_client.block_partner(admin.id, partner_id)


@partners_router.post(
    "/{partner_id}/unblock",
    summary="Разблокировать партнёра",
    responses=error_responses(401, 403),
)
async def unblock_partner(partner_id: UUID, admin: CurrentAdmin) -> dict[str, Any]:
    """Снимает блокировку/приостановку партнёра. Статус меняет
    partner-service. 401/403 — проблема с авторизацией админа."""
    return await partner_client.unblock_partner(admin.id, partner_id)
