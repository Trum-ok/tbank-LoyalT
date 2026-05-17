from fastapi import APIRouter, status

from app.deps import SessionDep
from app.domains.inbox.handlers import handle_event
from app.domains.inbox.schemas import IncomingEvent

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post(
    "/events",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Принять событие (имитация Kafka)",
)
async def ingest_event(event: IncomingEvent, session: SessionDep) -> dict[str, bool]:
    """Точка имитации входящих Kafka-событий для локальной разработки.

    Когда `NOTIFICATION_KAFKA_ENABLED=true`, события придут через consumer
    автоматически и эта ручка не нужна — но остаётся полезной для тестов.
    """
    handled = await handle_event(session, event.type, event.payload)
    return {"handled": handled}
