from uuid import UUID

from fastapi import APIRouter, Query, status
from loyalt_common import error_responses

from app.deps import CurrentAccountId, CurrentAdminId, SessionDep
from app.domains.applications import service
from app.domains.applications.models import ApplicationStatus
from app.domains.applications.schemas import (
    ApplicationCreate,
    ApplicationDecision,
    ApplicationRead,
    ApplicationUpdate,
)
from app.domains.partners import service as partners_service
from app.domains.partners.schemas import PartnerRead

partner_router = APIRouter(prefix="/applications", tags=["applications"])
admin_router = APIRouter(prefix="/admin/applications", tags=["applications-admin"])


@partner_router.post(
    "",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Подать заявку партнёра",
    responses=error_responses(404, 409),
)
async def submit_application(
    data: ApplicationCreate,
    account_id: CurrentAccountId,
    session: SessionDep,
) -> ApplicationRead:
    """Подаёт заявку на подключение бизнеса к платформе.

    Один аккаунт — одна активная заявка; повторная подача возможна только
    после отклонения предыдущей. 404 — аккаунт не найден; 409 — уже есть
    заявка в статусе pending/approved.
    """
    application = await service.submit_application(session, account_id, data)
    return ApplicationRead.model_validate(application)


@partner_router.get(
    "/me",
    response_model=list[ApplicationRead],
    summary="Мои заявки",
)
async def list_my_applications(
    account_id: CurrentAccountId, session: SessionDep
) -> list[ApplicationRead]:
    """Все заявки текущего аккаунта (история подач)."""
    applications = await service.list_my_applications(session, account_id)
    return [ApplicationRead.model_validate(a) for a in applications]


@partner_router.patch(
    "/me/{application_id}",
    response_model=ApplicationRead,
    summary="Изменить мою заявку",
    responses=error_responses(400, 403, 404),
)
async def update_my_application(
    application_id: UUID,
    data: ApplicationUpdate,
    account_id: CurrentAccountId,
    session: SessionDep,
) -> ApplicationRead:
    """Правит заявку, пока она на модерации.

    404 — заявка не найдена; 403 — заявка другого аккаунта; 400 — заявку
    уже рассмотрели, редактировать нельзя.
    """
    application = await service.update_my_pending(
        session, account_id, application_id, data
    )
    return ApplicationRead.model_validate(application)


@partner_router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отозвать мою заявку",
)
async def withdraw_my_application(
    account_id: CurrentAccountId, session: SessionDep
) -> None:
    """Удаляет заявку текущего аккаунта, пока она в статусе pending."""
    await service.withdraw_my_pending(session, account_id)


@admin_router.get(
    "",
    response_model=list[ApplicationRead],
    summary="Список заявок (модерация)",
)
async def list_applications(
    session: SessionDep,
    _admin: CurrentAdminId,
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ApplicationRead]:
    """Очередь заявок для панели Т-Банка с фильтром по статусу и пагинацией."""
    applications = await service.list_applications(
        session, status_filter=status_filter, limit=limit, offset=offset
    )
    return [ApplicationRead.model_validate(a) for a in applications]


@admin_router.get(
    "/{application_id}",
    response_model=ApplicationRead,
    summary="Карточка заявки",
    responses=error_responses(404),
)
async def get_application(
    application_id: UUID,
    session: SessionDep,
    _admin: CurrentAdminId,
) -> ApplicationRead:
    """Детали одной заявки. 404 — заявка не найдена."""
    application = await service.get_application(session, application_id)
    return ApplicationRead.model_validate(application)


@admin_router.post(
    "/{application_id}/approve",
    response_model=PartnerRead,
    summary="Одобрить заявку",
    responses=error_responses(400, 404, 409),
)
async def approve_application(
    application_id: UUID,
    data: ApplicationDecision,
    admin_id: CurrentAdminId,
    session: SessionDep,
) -> PartnerRead:
    """Одобряет заявку и создаёт партнёра в одной транзакции.

    Публикует событие `partner.approved`. 404 — заявка не найдена;
    400 — заявка уже рассмотрена; 409 — партнёр с таким ИНН/аккаунтом
    уже существует.
    """
    partner = await partners_service.approve_application_and_create_partner(
        session, application_id, admin_id, data.comment
    )
    return PartnerRead.model_validate(partner)


@admin_router.post(
    "/{application_id}/reject",
    response_model=ApplicationRead,
    summary="Отклонить заявку",
    responses=error_responses(400, 404),
)
async def reject_application(
    application_id: UUID,
    data: ApplicationDecision,
    admin_id: CurrentAdminId,
    session: SessionDep,
) -> ApplicationRead:
    """Отклоняет заявку с комментарием.

    404 — заявка не найдена; 400 — заявка уже рассмотрена.
    """
    application = await service.reject(session, application_id, admin_id, data.comment)
    return ApplicationRead.model_validate(application)
