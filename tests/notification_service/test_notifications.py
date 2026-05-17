import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

SERVICE_ROOT = Path(__file__).parents[2] / "services" / "notification-service"
sys.path.insert(0, str(SERVICE_ROOT))

from app.domains.notifications import service  # noqa: E402
from app.domains.notifications.models import (  # noqa: E402
    DeliveryStatus,
    NotificationType,
)
from app.domains.notifications.schemas import NotificationCreate  # noqa: E402
from app.errors import ForbiddenError, NotFoundError  # noqa: E402


def _payload(customer_id, **kwargs) -> NotificationCreate:
    base = {
        "customer_id": customer_id,
        "type": NotificationType.POINTS_ACCRUED,
        "title": "+80 баллов",
        "body": "Кофе Хауз",
    }
    return NotificationCreate(**{**base, **kwargs})


class TestCreateAndDeliver:
    async def test_skipped_without_devices(self, session: AsyncSession, customer_id):
        n = await service.create_and_deliver(session, _payload(customer_id))
        assert n.delivery_status == DeliveryStatus.SKIPPED
        assert n.delivery_error == "No active devices"

    async def test_sent_with_active_device(self, session: AsyncSession, active_device):
        n = await service.create_and_deliver(
            session, _payload(active_device.customer_id)
        )
        assert n.delivery_status == DeliveryStatus.SENT
        assert n.delivered_at is not None


class TestListForCustomer:
    async def test_unread_only_filter(self, session: AsyncSession, customer_id):
        n1 = await service.create_and_deliver(session, _payload(customer_id))
        await service.create_and_deliver(session, _payload(customer_id))
        await service.mark_read(session, customer_id, n1.id)

        unread = await service.list_for_customer(session, customer_id, unread_only=True)
        assert len(unread) == 1
        assert all(not n.is_read for n in unread)


class TestMarkRead:
    async def test_mark_read_sets_flag(self, session: AsyncSession, customer_id):
        n = await service.create_and_deliver(session, _payload(customer_id))
        updated = await service.mark_read(session, customer_id, n.id)
        assert updated.is_read is True

    async def test_foreign_notification_forbidden(
        self, session: AsyncSession, customer_id
    ):
        n = await service.create_and_deliver(session, _payload(customer_id))
        with pytest.raises(ForbiddenError):
            await service.mark_read(session, uuid4(), n.id)

    async def test_missing_notification_raises(
        self, session: AsyncSession, customer_id
    ):
        with pytest.raises(NotFoundError):
            await service.mark_read(session, customer_id, uuid4())
