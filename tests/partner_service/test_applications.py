import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

SERVICE_ROOT = Path(__file__).parents[2] / "services" / "partner-service"
sys.path.insert(0, str(SERVICE_ROOT))

from app.domains.applications import service  # noqa: E402
from app.domains.applications.models import (  # noqa: E402
    ApplicationStatus,
    PartnerCategory,
)
from app.domains.applications.schemas import (  # noqa: E402
    ApplicationCreate,
    ApplicationUpdate,
)
from app.errors import (  # noqa: E402
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)


def _payload(**kwargs) -> ApplicationCreate:
    base = {
        "business_name": "Кофейня",
        "inn": "7701234567",
        "categories": [PartnerCategory.FOOD],
        "contact_email": "owner@coffee.ru",
    }
    return ApplicationCreate(**{**base, **kwargs})


class TestSubmitApplication:
    async def test_submit_creates_pending(self, session: AsyncSession, account_id):
        app = await service.submit_application(session, account_id, _payload())
        assert app.status == ApplicationStatus.PENDING
        assert app.categories == ["food"]
        assert app.contact_email == "owner@coffee.ru"

    async def test_contact_email_lowercased(self, session: AsyncSession, account_id):
        app = await service.submit_application(
            session, account_id, _payload(contact_email="OWNER@Coffee.RU")
        )
        assert app.contact_email == "owner@coffee.ru"

    async def test_submit_for_missing_account_raises(self, session: AsyncSession):
        with pytest.raises(NotFoundError):
            await service.submit_application(session, uuid4(), _payload())

    async def test_second_pending_application_conflicts(
        self, session: AsyncSession, account_id
    ):
        await service.submit_application(session, account_id, _payload())
        with pytest.raises(ConflictError):
            await service.submit_application(session, account_id, _payload())

    async def test_resubmit_allowed_after_reject(
        self, session: AsyncSession, account_id
    ):
        app = await service.submit_application(session, account_id, _payload())
        await service.reject(session, app.id, uuid4(), "не подходит")
        again = await service.submit_application(session, account_id, _payload())
        assert again.status == ApplicationStatus.PENDING


class TestDecisions:
    async def test_approve_sets_fields(self, session: AsyncSession, account_id):
        app = await service.submit_application(session, account_id, _payload())
        admin_id = uuid4()
        approved = await service.approve(session, app.id, admin_id, "ок")
        assert approved.status == ApplicationStatus.APPROVED
        assert approved.decided_by == admin_id
        assert approved.decision_comment == "ок"

    async def test_reject_sets_status(self, session: AsyncSession, account_id):
        app = await service.submit_application(session, account_id, _payload())
        rejected = await service.reject(session, app.id, uuid4())
        assert rejected.status == ApplicationStatus.REJECTED

    async def test_reject_twice_raises(self, session: AsyncSession, account_id):
        app = await service.submit_application(session, account_id, _payload())
        await service.reject(session, app.id, uuid4())
        with pytest.raises(BadRequestError, match="already"):
            await service.reject(session, app.id, uuid4())

    async def test_decision_on_missing_raises(self, session: AsyncSession):
        with pytest.raises(NotFoundError):
            await service.reject(session, uuid4(), uuid4())


class TestMyApplications:
    async def test_withdraw_removes_pending(self, session: AsyncSession, account_id):
        await service.submit_application(session, account_id, _payload())
        await service.withdraw_my_pending(session, account_id)
        assert await service.list_my_applications(session, account_id) == []

    async def test_update_pending_changes_fields(
        self, session: AsyncSession, account_id
    ):
        app = await service.submit_application(session, account_id, _payload())
        updated = await service.update_my_pending(
            session,
            account_id,
            app.id,
            ApplicationUpdate(business_name="Новое название"),
        )
        assert updated.business_name == "Новое название"

    async def test_update_foreign_application_forbidden(
        self, session: AsyncSession, account_id
    ):
        app = await service.submit_application(session, account_id, _payload())
        with pytest.raises(ForbiddenError):
            await service.update_my_pending(
                session,
                uuid4(),
                app.id,
                ApplicationUpdate(business_name="Чужое"),
            )
