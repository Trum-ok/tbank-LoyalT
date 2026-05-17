import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

SERVICE_ROOT = Path(__file__).parents[2] / "services" / "core-service"
sys.path.insert(0, str(SERVICE_ROOT))

from app.domains.programs import trigger_service  # noqa: E402
from app.domains.programs.models import TriggerType  # noqa: E402
from app.domains.programs.trigger_schemas import (  # noqa: E402
    BonusTriggerCreate,
    BonusTriggerUpdate,
)
from app.errors import BadRequestError, ForbiddenError, NotFoundError  # noqa: E402


def _manual(name: str = "Ручная", points: int = 100) -> BonusTriggerCreate:
    return BonusTriggerCreate(type=TriggerType.MANUAL, name=name, points=points)


def _fixed(name: str = "Акция", points: int = 50) -> BonusTriggerCreate:
    from datetime import date

    return BonusTriggerCreate(
        type=TriggerType.FIXED_DATE,
        name=name,
        points=points,
        fire_date=date(2030, 1, 1),
    )


class TestTriggerCRUD:
    async def test_create_returns_trigger(self, session: AsyncSession, program, partner_id):
        trigger = await trigger_service.create_trigger(
            session, program.id, partner_id, _manual()
        )
        assert trigger.id is not None
        assert trigger.type == TriggerType.MANUAL
        assert trigger.name == "Ручная"
        assert trigger.points == 100
        assert trigger.is_active is True

    async def test_list_returns_created_triggers(
        self, session: AsyncSession, program, partner_id
    ):
        await trigger_service.create_trigger(session, program.id, partner_id, _manual("A"))
        await trigger_service.create_trigger(session, program.id, partner_id, _manual("B"))

        triggers = await trigger_service.list_triggers(session, program.id, partner_id)
        assert len(triggers) == 2
        names = {t.name for t in triggers}
        assert names == {"A", "B"}

    async def test_list_empty_for_new_program(
        self, session: AsyncSession, program, partner_id
    ):
        triggers = await trigger_service.list_triggers(session, program.id, partner_id)
        assert triggers == []

    async def test_list_rejects_foreign_partner(
        self, session: AsyncSession, program, partner_id
    ):
        # IDOR-регрессия: чужой партнёр не должен видеть кампании по UUID
        # программы — list_triggers обязан проверять владение.
        await trigger_service.create_trigger(
            session, program.id, partner_id, _manual("A")
        )
        with pytest.raises(ForbiddenError):
            await trigger_service.list_triggers(session, program.id, uuid4())

    async def test_update_name_and_points(
        self, session: AsyncSession, program, partner_id
    ):
        trigger = await trigger_service.create_trigger(
            session, program.id, partner_id, _manual()
        )
        updated = await trigger_service.update_trigger(
            session,
            program.id,
            trigger.id,
            partner_id,
            BonusTriggerUpdate(name="Новое имя", points=200),
        )
        assert updated.name == "Новое имя"
        assert updated.points == 200

    async def test_update_deactivate(self, session: AsyncSession, program, partner_id):
        trigger = await trigger_service.create_trigger(
            session, program.id, partner_id, _manual()
        )
        updated = await trigger_service.update_trigger(
            session,
            program.id,
            trigger.id,
            partner_id,
            BonusTriggerUpdate(is_active=False),
        )
        assert updated.is_active is False

    async def test_delete_removes_trigger(self, session: AsyncSession, program, partner_id):
        trigger = await trigger_service.create_trigger(
            session, program.id, partner_id, _manual()
        )
        await trigger_service.delete_trigger(
            session, program.id, trigger.id, partner_id
        )
        triggers = await trigger_service.list_triggers(session, program.id, partner_id)
        assert triggers == []

    async def test_update_nonexistent_trigger_raises(
        self, session: AsyncSession, program, partner_id
    ):
        with pytest.raises(NotFoundError):
            await trigger_service.update_trigger(
                session,
                program.id,
                uuid4(),
                partner_id,
                BonusTriggerUpdate(name="X"),
            )

    async def test_delete_nonexistent_trigger_raises(
        self, session: AsyncSession, program, partner_id
    ):
        with pytest.raises(NotFoundError):
            await trigger_service.delete_trigger(
                session, program.id, uuid4(), partner_id
            )

    async def test_wrong_partner_raises_forbidden(
        self, session: AsyncSession, program, partner_id
    ):
        other_partner_id = uuid4()
        with pytest.raises(ForbiddenError):
            await trigger_service.create_trigger(
                session, program.id, other_partner_id, _manual()
            )

    async def test_trigger_belongs_to_another_program_raises(
        self, session: AsyncSession, program, partner_id
    ):
        from app.domains.programs import service as program_service
        from app.domains.programs.schemas import ProgramCreate
        from app.domains.programs.models import ProgramType

        other = await program_service.create_program(
            session,
            partner_id,
            ProgramCreate(name="Другая", type=ProgramType.ACCRUAL, accrual_rule={"percent": 1}),
        )
        trigger = await trigger_service.create_trigger(
            session, program.id, partner_id, _manual()
        )
        with pytest.raises(NotFoundError):
            await trigger_service.delete_trigger(
                session, other.id, trigger.id, partner_id
            )


class TestFireTrigger:
    async def test_fire_manual_returns_count(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        trigger = await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            BonusTriggerCreate(type=TriggerType.MANUAL, name="Акция", points=50),
        )
        count = await trigger_service.fire_trigger(
            session, trigger.id, published_program.id, partner_id
        )
        assert count == 1

    async def test_fire_accrues_points_to_enrollment(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        trigger = await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            BonusTriggerCreate(type=TriggerType.MANUAL, name="Акция", points=50),
        )
        await trigger_service.fire_trigger(
            session, trigger.id, published_program.id, partner_id
        )
        await session.refresh(enrollment)
        assert enrollment.points_balance == 50

    async def test_fire_non_manual_raises(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        trigger = await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _fixed(),
        )
        with pytest.raises(BadRequestError, match="MANUAL"):
            await trigger_service.fire_trigger(
                session, trigger.id, published_program.id, partner_id
            )

    async def test_fire_nonexistent_trigger_raises(
        self, session: AsyncSession, published_program, partner_id
    ):
        with pytest.raises(NotFoundError):
            await trigger_service.fire_trigger(
                session, uuid4(), published_program.id, partner_id
            )

    async def test_fire_zero_enrollments_returns_zero(
        self, session: AsyncSession, published_program, partner_id
    ):
        trigger = await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            BonusTriggerCreate(type=TriggerType.MANUAL, name="Пусто", points=10),
        )
        count = await trigger_service.fire_trigger(
            session, trigger.id, published_program.id, partner_id
        )
        assert count == 0
