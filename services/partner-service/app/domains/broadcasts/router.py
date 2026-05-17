from uuid import UUID

from fastapi import APIRouter, Query, status
from loyalt_common import error_responses

from app.deps import CurrentPartnerId, SessionDep
from app.domains.broadcasts import service
from app.domains.broadcasts.models import BroadcastSegment
from app.domains.broadcasts.schemas import (
    AudiencePreview,
    BroadcastCreate,
    BroadcastRead,
    BroadcastUpdate,
)

router = APIRouter(prefix="/broadcasts", tags=["broadcasts"])


@router.get(
    "",
    response_model=list[BroadcastRead],
    summary="Мои рассылки",
)
async def list_my_broadcasts(
    partner_id: CurrentPartnerId, session: SessionDep
) -> list[BroadcastRead]:
    """Все рассылки партнёра (черновики и отправленные)."""
    rows = await service.list_broadcasts(session, partner_id)
    return [BroadcastRead.model_validate(b) for b in rows]


@router.get(
    "/audience",
    response_model=AudiencePreview,
    summary="Размер аудитории",
)
async def preview_audience(
    partner_id: CurrentPartnerId,
    session: SessionDep,
    segment: BroadcastSegment = Query(default=BroadcastSegment.ALL_ENROLLED),
    program_id: UUID | None = Query(default=None),
) -> AudiencePreview:
    """Сколько клиентов попадёт в рассылку по выбранному сегменту
    (резолвится синхронно в core-service)."""
    count = await service.audience_count(partner_id, segment, program_id)
    return AudiencePreview(count=count)


@router.post(
    "",
    response_model=BroadcastRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать черновик рассылки",
)
async def create_broadcast(
    data: BroadcastCreate,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> BroadcastRead:
    """Создаёт рассылку в статусе draft (без отправки)."""
    broadcast = await service.create_draft(session, partner_id, data)
    return BroadcastRead.model_validate(broadcast)


@router.get(
    "/{broadcast_id}",
    response_model=BroadcastRead,
    summary="Карточка рассылки",
    responses=error_responses(403, 404),
)
async def get_broadcast(
    broadcast_id: UUID,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> BroadcastRead:
    """Детали рассылки. 404 — не найдена; 403 — рассылка другого партнёра."""
    broadcast = await service.get_broadcast(session, partner_id, broadcast_id)
    return BroadcastRead.model_validate(broadcast)


@router.patch(
    "/{broadcast_id}",
    response_model=BroadcastRead,
    summary="Изменить черновик рассылки",
    responses=error_responses(400, 403, 404),
)
async def update_broadcast(
    broadcast_id: UUID,
    data: BroadcastUpdate,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> BroadcastRead:
    """Правит рассылку, пока она в статусе draft.

    404 — не найдена; 403 — рассылка другого партнёра; 400 — рассылка
    уже отправлена, редактировать нельзя.
    """
    broadcast = await service.update_draft(session, partner_id, broadcast_id, data)
    return BroadcastRead.model_validate(broadcast)


@router.delete(
    "/{broadcast_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить черновик рассылки",
    responses=error_responses(400, 403, 404),
)
async def delete_broadcast(
    broadcast_id: UUID,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> None:
    """Удаляет рассылку в статусе draft.

    404 — не найдена; 403 — рассылка другого партнёра; 400 — рассылка
    уже отправлена, удалить нельзя.
    """
    await service.delete_draft(session, partner_id, broadcast_id)


@router.post(
    "/{broadcast_id}/send",
    response_model=BroadcastRead,
    summary="Отправить рассылку",
    responses=error_responses(400, 403, 404),
)
async def send_broadcast(
    broadcast_id: UUID,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> BroadcastRead:
    """Резолвит аудиторию и публикует `partner.broadcast` (фан-аут уведомлений).

    404 — не найдена; 403 — рассылка другого партнёра; 400 — рассылка
    уже отправлена.
    """
    broadcast = await service.send_broadcast(session, partner_id, broadcast_id)
    return BroadcastRead.model_validate(broadcast)
