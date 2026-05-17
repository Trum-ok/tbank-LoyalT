"""Тесты фонового воркера бонусных кампаний."""

import sys
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

SERVICE_ROOT = Path(__file__).parents[2] / "services" / "core-service"
sys.path.insert(0, str(SERVICE_ROOT))

from app.domains.enrollments.models import Customer  # noqa: E402
from app.domains.points.bonus_campaigns import run_bonus_campaigns  # noqa: E402
from app.domains.programs import trigger_service  # noqa: E402
from app.domains.programs.models import TriggerType  # noqa: E402
from app.domains.programs.trigger_schemas import BonusTriggerCreate  # noqa: E402

TODAY = date(2025, 6, 15)


def _trigger(type: TriggerType, points: int = 100, **kwargs) -> BonusTriggerCreate:
    return BonusTriggerCreate(type=type, name=f"{type}-кампания", points=points, **kwargs)


@pytest_asyncio.fixture
async def customer_with_birthday(session: AsyncSession, customer_id):
    """Клиент с датой рождения 15 июня."""
    customer = await session.get(Customer, customer_id)
    customer.birthday = date(1990, 6, 15)
    await session.commit()
    return customer


class TestFixedDateTrigger:
    async def test_fires_on_matching_date(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.FIXED_DATE, fire_date=TODAY),
        )
        count = await run_bonus_campaigns(session, today=TODAY)
        assert count == 1
        await session.refresh(enrollment)
        assert enrollment.points_balance == 100

    async def test_does_not_fire_on_wrong_date(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.FIXED_DATE, fire_date=TODAY + timedelta(days=1)),
        )
        count = await run_bonus_campaigns(session, today=TODAY)
        assert count == 0

    async def test_repeat_yearly_fires_by_month_and_day(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(
                TriggerType.FIXED_DATE,
                fire_date=date(2020, 6, 15),
                repeat_yearly=True,
            ),
        )
        count = await run_bonus_campaigns(session, today=TODAY)
        assert count == 1

    async def test_repeat_yearly_does_not_fire_on_different_day(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(
                TriggerType.FIXED_DATE,
                fire_date=date(2020, 6, 16),
                repeat_yearly=True,
            ),
        )
        count = await run_bonus_campaigns(session, today=TODAY)
        assert count == 0

    async def test_idempotent_on_same_day(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.FIXED_DATE, fire_date=TODAY),
        )
        await run_bonus_campaigns(session, today=TODAY)
        count2 = await run_bonus_campaigns(session, today=TODAY)
        assert count2 == 0
        await session.refresh(enrollment)
        assert enrollment.points_balance == 100


class TestBirthdayTrigger:
    async def test_fires_on_birthday(
        self,
        session: AsyncSession,
        published_program,
        partner_id,
        enrollment,
        customer_with_birthday,
    ):
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.BIRTHDAY),
        )
        count = await run_bonus_campaigns(session, today=TODAY)
        assert count == 1

    async def test_fires_days_before_birthday(
        self,
        session: AsyncSession,
        published_program,
        partner_id,
        enrollment,
        customer_with_birthday,
    ):
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.BIRTHDAY, days_before=3),
        )
        count = await run_bonus_campaigns(
            session, today=date(2025, 6, 12)  # 15 - 3
        )
        assert count == 1

    async def test_does_not_fire_wrong_day(
        self,
        session: AsyncSession,
        published_program,
        partner_id,
        enrollment,
        customer_with_birthday,
    ):
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.BIRTHDAY),
        )
        count = await run_bonus_campaigns(session, today=date(2025, 6, 14))
        assert count == 0

    async def test_does_not_fire_without_birthday(
        self,
        session: AsyncSession,
        published_program,
        partner_id,
        enrollment,
        customer_id,
    ):
        # customer_id фикстура создаёт клиента без ДР
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.BIRTHDAY),
        )
        count = await run_bonus_campaigns(session, today=TODAY)
        assert count == 0

    async def test_idempotent_on_same_day(
        self,
        session: AsyncSession,
        published_program,
        partner_id,
        enrollment,
        customer_with_birthday,
    ):
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.BIRTHDAY),
        )
        await run_bonus_campaigns(session, today=TODAY)
        count2 = await run_bonus_campaigns(session, today=TODAY)
        assert count2 == 0


class TestIntervalTrigger:
    async def test_fires_on_nth_day(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        # enrollment создан сегодня, запускаем через 7 дней
        enroll_date = enrollment.created_at.date()
        fire_date = enroll_date + timedelta(days=7)
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.INTERVAL, interval_days=7),
        )
        count = await run_bonus_campaigns(session, today=fire_date)
        assert count == 1

    async def test_does_not_fire_too_early(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        enroll_date = enrollment.created_at.date()
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.INTERVAL, interval_days=7),
        )
        count = await run_bonus_campaigns(
            session, today=enroll_date + timedelta(days=6)
        )
        assert count == 0

    async def test_repeat_interval_fires_every_n_days(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        enroll_date = enrollment.created_at.date()
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.INTERVAL, interval_days=7, repeat_interval=True),
        )
        count_7 = await run_bonus_campaigns(
            session, today=enroll_date + timedelta(days=7)
        )
        count_14 = await run_bonus_campaigns(
            session, today=enroll_date + timedelta(days=14)
        )
        assert count_7 == 1
        assert count_14 == 1

    async def test_repeat_interval_does_not_fire_between(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        enroll_date = enrollment.created_at.date()
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.INTERVAL, interval_days=7, repeat_interval=True),
        )
        count = await run_bonus_campaigns(
            session, today=enroll_date + timedelta(days=8)
        )
        assert count == 0


class TestInactivityTrigger:
    async def test_fires_when_no_recent_transactions(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.INACTIVITY, interval_days=30),
        )
        # enrollment только создан, транзакций нет
        count = await run_bonus_campaigns(session, today=TODAY)
        assert count == 1

    async def test_does_not_fire_when_recent_transaction_exists(
        self, session: AsyncSession, published_program, partner_id, enrollment, customer_id
    ):
        from app.domains.transactions.models import Transaction, TransactionType

        recent_tx = Transaction(
            enrollment_id=enrollment.id,
            customer_id=customer_id,
            program_id=published_program.id,
            partner_id=partner_id,
            type=TransactionType.ACCRUAL,
            points=10,
        )
        session.add(recent_tx)
        await session.commit()

        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.INACTIVITY, interval_days=30),
        )
        count = await run_bonus_campaigns(session, today=TODAY)
        assert count == 0

    async def test_idempotent_in_inactivity_window(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.INACTIVITY, interval_days=30),
        )
        await run_bonus_campaigns(session, today=TODAY)
        count2 = await run_bonus_campaigns(
            session, today=TODAY + timedelta(days=1)
        )
        assert count2 == 0


class TestWorkerBehavior:
    async def test_manual_trigger_is_skipped(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            _trigger(TriggerType.MANUAL),
        )
        count = await run_bonus_campaigns(session, today=TODAY)
        assert count == 0

    async def test_inactive_trigger_is_skipped(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        await trigger_service.create_trigger(
            session,
            published_program.id,
            partner_id,
            BonusTriggerCreate(
                type=TriggerType.FIXED_DATE,
                name="Неактивная",
                points=100,
                fire_date=TODAY,
                is_active=False,
            ),
        )
        count = await run_bonus_campaigns(session, today=TODAY)
        assert count == 0

    async def test_no_triggers_returns_zero(
        self, session: AsyncSession, published_program, partner_id, enrollment
    ):
        count = await run_bonus_campaigns(session, today=TODAY)
        assert count == 0
