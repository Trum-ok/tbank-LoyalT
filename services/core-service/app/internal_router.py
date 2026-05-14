from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.deps import SessionDep
from app.inbox import handle_event

router = APIRouter(prefix="/internal", tags=["internal"])


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
