import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

SERVICE_ROOT = Path(__file__).parents[2] / "services" / "notification-service"
sys.path.insert(0, str(SERVICE_ROOT))

from app.domains.devices import service  # noqa: E402
from app.domains.devices.models import DevicePlatform  # noqa: E402
from app.domains.devices.schemas import DeviceRegister  # noqa: E402
from app.errors import NotFoundError  # noqa: E402


class TestRegisterDevice:
    async def test_register_creates_device(self, session: AsyncSession, customer_id):
        d = await service.register_device(
            session,
            customer_id,
            DeviceRegister(token="tok-1", platform=DevicePlatform.IOS),
        )
        assert d.is_active is True
        assert d.customer_id == customer_id

    async def test_same_token_is_idempotent(
        self, session: AsyncSession, customer_id
    ):
        first = await service.register_device(
            session,
            customer_id,
            DeviceRegister(token="tok-2", platform=DevicePlatform.IOS),
        )
        second = await service.register_device(
            session,
            customer_id,
            DeviceRegister(token="tok-2", platform=DevicePlatform.ANDROID),
        )
        assert second.id == first.id
        assert second.platform == DevicePlatform.ANDROID
        assert len(await service.list_devices(session, customer_id)) == 1


class TestListDevices:
    async def test_lists_only_active(self, session: AsyncSession, customer_id):
        await service.register_device(
            session,
            customer_id,
            DeviceRegister(token="tok-3", platform=DevicePlatform.WEB),
        )
        d2 = await service.register_device(
            session,
            customer_id,
            DeviceRegister(token="tok-4", platform=DevicePlatform.WEB),
        )
        await service.deactivate(session, customer_id, d2.id)

        active = await service.list_devices(session, customer_id)
        assert [d.token for d in active] == ["tok-3"]


class TestDeactivate:
    async def test_foreign_device_raises_not_found(
        self, session: AsyncSession, active_device
    ):
        with pytest.raises(NotFoundError):
            await service.deactivate(session, uuid4(), active_device.id)

    async def test_missing_device_raises_not_found(
        self, session: AsyncSession, customer_id
    ):
        with pytest.raises(NotFoundError):
            await service.deactivate(session, customer_id, uuid4())
