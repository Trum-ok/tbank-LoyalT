import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

SERVICE_ROOT = Path(__file__).parents[2] / "services" / "partner-service"
sys.path.insert(0, str(SERVICE_ROOT))

from app.domains.accounts import service  # noqa: E402
from app.domains.accounts.schemas import AccountCreate, AccountUpdate  # noqa: E402
from app.errors import ConflictError, NotFoundError  # noqa: E402


class TestCreateAccount:
    async def test_create_returns_account(self, session: AsyncSession):
        acc = await service.create_account(
            session, AccountCreate(email="a@b.ru", full_name="Тест")
        )
        assert acc.id is not None
        assert acc.full_name == "Тест"

    async def test_email_is_lowercased(self, session: AsyncSession):
        acc = await service.create_account(
            session, AccountCreate(email="OWNER@Coffee.RU")
        )
        assert acc.email == "owner@coffee.ru"

    async def test_duplicate_email_raises_conflict(self, session: AsyncSession):
        await service.create_account(session, AccountCreate(email="dup@b.ru"))
        with pytest.raises(ConflictError, match="already exists"):
            await service.create_account(session, AccountCreate(email="dup@b.ru"))


class TestGetAccount:
    async def test_get_existing(self, session: AsyncSession, account):
        found = await service.get_account(session, account.id)
        assert found.id == account.id

    async def test_get_missing_raises_not_found(self, session: AsyncSession):
        with pytest.raises(NotFoundError):
            await service.get_account(session, uuid4())


class TestUpdateAccount:
    async def test_update_changes_fields(self, session: AsyncSession, account):
        updated = await service.update_account(
            session, account.id, AccountUpdate(full_name="Новое Имя")
        )
        assert updated.full_name == "Новое Имя"

    async def test_update_missing_raises_not_found(self, session: AsyncSession):
        with pytest.raises(NotFoundError):
            await service.update_account(session, uuid4(), AccountUpdate(full_name="X"))
