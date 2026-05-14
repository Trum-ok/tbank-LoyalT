from uuid import UUID

from fastapi import APIRouter, Query

from app.deps import CurrentCustomerId, SessionDep
from app.domains.notifications import service
from app.domains.notifications.schemas import NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
async def list_my_notifications(
    customer_id: CurrentCustomerId,
    session: SessionDep,
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[NotificationRead]:
    notifications = await service.list_for_customer(
        session, customer_id, unread_only=unread_only, limit=limit, offset=offset
    )
    return [NotificationRead.model_validate(n) for n in notifications]


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(
    notification_id: UUID,
    customer_id: CurrentCustomerId,
    session: SessionDep,
) -> NotificationRead:
    notification = await service.mark_read(session, customer_id, notification_id)
    return NotificationRead.model_validate(notification)
