import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

SERVICE_ROOT = Path(__file__).parents[2] / "services" / "admin-service"
sys.path.insert(0, str(SERVICE_ROOT))

from app.domains.admins import service  # noqa: E402
from app.domains.admins.schemas import AdminCreate, AdminUpdate  # noqa: E402
from app.errors import ConflictError, NotFoundError  # noqa: E402


class TestCreateAdmin:
    async def test_create_returns_admin(self, session: AsyncSession):
        admin = await service.create_admin(
            session, AdminCreate(email="mod@tbank.ru", full_name="Модератор")
        )
        assert admin.id is not None
        assert admin.is_active is True

    async def test_email_lowercased(self, session: AsyncSession):
        admin = await service.create_admin(session, AdminCreate(email="MOD@Tbank.RU"))
        assert admin.email == "mod@tbank.ru"

    async def test_duplicate_email_conflicts(self, session: AsyncSession):
        await service.create_admin(session, AdminCreate(email="dup@tbank.ru"))
        with pytest.raises(ConflictError, match="already exists"):
            await service.create_admin(session, AdminCreate(email="dup@tbank.ru"))


class TestCountAdmins:
    async def test_zero_on_empty(self, session: AsyncSession):
        assert await service.count_admins(session) == 0

    async def test_counts_created(self, session: AsyncSession):
        await service.create_admin(session, AdminCreate(email="a@tbank.ru"))
        await service.create_admin(session, AdminCreate(email="b@tbank.ru"))
        assert await service.count_admins(session) == 2


class TestGetUpdateAdmin:
    async def test_get_missing_raises(self, session: AsyncSession):
        with pytest.raises(NotFoundError):
            await service.get_admin(session, uuid4())

    async def test_update_deactivates(self, session: AsyncSession):
        admin = await service.create_admin(session, AdminCreate(email="c@tbank.ru"))
        updated = await service.update_admin(
            session, admin.id, AdminUpdate(is_active=False)
        )
        assert updated.is_active is False
