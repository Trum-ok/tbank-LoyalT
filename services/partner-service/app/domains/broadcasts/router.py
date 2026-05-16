from uuid import UUID

from fastapi import APIRouter, Query, status

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


@router.get("", response_model=list[BroadcastRead])
async def list_my_broadcasts(
    partner_id: CurrentPartnerId, session: SessionDep
) -> list[BroadcastRead]:
    rows = await service.list_broadcasts(session, partner_id)
    return [BroadcastRead.model_validate(b) for b in rows]


@router.get("/audience", response_model=AudiencePreview)
async def preview_audience(
    partner_id: CurrentPartnerId,
    session: SessionDep,
    segment: BroadcastSegment = Query(default=BroadcastSegment.ALL_ENROLLED),
    program_id: UUID | None = Query(default=None),
) -> AudiencePreview:
    count = await service.audience_count(partner_id, segment, program_id)
    return AudiencePreview(count=count)


@router.post("", response_model=BroadcastRead, status_code=status.HTTP_201_CREATED)
async def create_broadcast(
    data: BroadcastCreate,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> BroadcastRead:
    broadcast = await service.create_draft(session, partner_id, data)
    return BroadcastRead.model_validate(broadcast)


@router.get("/{broadcast_id}", response_model=BroadcastRead)
async def get_broadcast(
    broadcast_id: UUID,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> BroadcastRead:
    broadcast = await service.get_broadcast(session, partner_id, broadcast_id)
    return BroadcastRead.model_validate(broadcast)


@router.patch("/{broadcast_id}", response_model=BroadcastRead)
async def update_broadcast(
    broadcast_id: UUID,
    data: BroadcastUpdate,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> BroadcastRead:
    broadcast = await service.update_draft(session, partner_id, broadcast_id, data)
    return BroadcastRead.model_validate(broadcast)


@router.delete("/{broadcast_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_broadcast(
    broadcast_id: UUID,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> None:
    await service.delete_draft(session, partner_id, broadcast_id)


@router.post("/{broadcast_id}/send", response_model=BroadcastRead)
async def send_broadcast(
    broadcast_id: UUID,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> BroadcastRead:
    broadcast = await service.send_broadcast(session, partner_id, broadcast_id)
    return BroadcastRead.model_validate(broadcast)
