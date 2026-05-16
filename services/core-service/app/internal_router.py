from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from app.audience import AudienceSegment, resolve_audience
from app.deps import SessionDep
from app.domains.analytics import projection
from app.inbox import handle_event

router = APIRouter(prefix="/internal", tags=["internal"])


class AudienceResponse(BaseModel):
    count: int
    customer_ids: list[UUID]


@router.get("/partner-audience", response_model=AudienceResponse)
async def partner_audience(
    session: SessionDep,
    partner_id: UUID,
    segment: AudienceSegment = Query(default=AudienceSegment.ALL_ENROLLED),
    program_id: UUID | None = Query(default=None),
) -> AudienceResponse:
    """Список customer_id для сегмента партнёра (для рассылок).

    Внутренний эндпоинт: вызывается partner-service по внутренней сети.
    """
    ids = await resolve_audience(session, partner_id, segment, program_id)
    return AudienceResponse(count=len(ids), customer_ids=ids)


class IncomingEvent(BaseModel):
    type: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(event: IncomingEvent, session: SessionDep) -> dict[str, bool]:
    """Точка имитации Kafka-событий для локальной разработки.

    Когда `CORE_KAFKA_ENABLED=true`, события придут через consumer
    автоматически.
    """
    handled = await handle_event(session, event.type, event.payload)
    return {"handled": handled}


@router.post("/analytics/rebuild", status_code=status.HTTP_200_OK)
async def rebuild_analytics(session: SessionDep) -> dict[str, int]:
    """Полная пересборка read-модели аналитики из transaction.

    Источник истины — transaction. Backfill уже накопленных данных и
    страховка паритета, если Kafka выключена или событие потерялось
    (outbox'а нет). Идемпотентна.
    """
    return await projection.rebuild_from_transactions(session)
