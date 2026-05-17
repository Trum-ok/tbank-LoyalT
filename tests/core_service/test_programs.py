import sys
from datetime import date, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

SERVICE_ROOT = Path(__file__).parents[2] / "services" / "core-service"
sys.path.insert(0, str(SERVICE_ROOT))

from app.domains.programs import service  # noqa: E402
from app.domains.programs.models import ProgramStatus, ProgramType  # noqa: E402
from app.domains.programs.schemas import (  # noqa: E402
    ProgramCreate,
    ProgramUpdate,
    TierCreate,
    TierUpdate,
)
from app.errors import BadRequestError, ForbiddenError, NotFoundError  # noqa: E402

_ACCRUAL_BASE = dict(type=ProgramType.ACCRUAL, accrual_rule={"percent": 5})


def _program(name: str = "Тест", **kwargs) -> ProgramCreate:
    return ProgramCreate(name=name, **{**_ACCRUAL_BASE, **kwargs})


class TestProgramSchemas:
    def test_valid_dates_pass(self):
        today = date.today()
        p = _program(valid_from=today, valid_until=today + timedelta(days=30))
        assert p.valid_from == today

    def test_reversed_dates_raise(self):
        today = date.today()
        with pytest.raises(ValueError, match="valid_from must be before valid_until"):
            _program(valid_from=today + timedelta(days=1), valid_until=today)

    def test_birthday_bonus_days_upper_bound(self):
        p = _program(birthday_bonus_points=100, birthday_bonus_days=30)
        assert p.birthday_bonus_days == 30

    def test_birthday_bonus_days_exceeds_limit(self):
        with pytest.raises(ValueError):
            _program(birthday_bonus_points=100, birthday_bonus_days=31)

    def test_max_redemption_percent_boundaries(self):
        _program(max_redemption_percent=1)
        _program(max_redemption_percent=100)

    def test_max_redemption_percent_zero_invalid(self):
        with pytest.raises(ValueError):
            _program(max_redemption_percent=0)

    def test_max_redemption_percent_over_100_invalid(self):
        with pytest.raises(ValueError):
            _program(max_redemption_percent=101)

    def test_welcome_bonus_must_be_positive(self):
        with pytest.raises(ValueError):
            _program(welcome_bonus_points=0)

    def test_min_purchase_amount_must_be_positive(self):
        with pytest.raises(ValueError):
            _program(min_purchase_amount=0)

    def test_all_new_fields_accepted(self):
        today = date.today()
        p = _program(
            welcome_bonus_points=200,
            birthday_bonus_points=50,
            birthday_bonus_days=7,
            referral_bonus_points=100,
            min_purchase_amount=10000,
            max_points_per_transaction=500,
            max_redemption_percent=50,
            valid_from=today,
            valid_until=today + timedelta(days=365),
        )
        assert p.welcome_bonus_points == 200
        assert p.referral_bonus_points == 100
        assert p.max_redemption_percent == 50

    def test_tier_multiplier_lower_bound(self):
        TierCreate(name="Bronze", threshold_points=0, accrual_multiplier=0.1)

    def test_tier_multiplier_upper_bound(self):
        TierCreate(name="VIP", threshold_points=10000, accrual_multiplier=10.0)

    def test_tier_multiplier_below_minimum(self):
        with pytest.raises(ValueError):
            TierCreate(name="Bad", threshold_points=0, accrual_multiplier=0.0)

    def test_tier_multiplier_above_maximum(self):
        with pytest.raises(ValueError):
            TierCreate(name="Bad", threshold_points=0, accrual_multiplier=10.1)

    def test_tier_negative_threshold_invalid(self):
        with pytest.raises(ValueError):
            TierCreate(name="Bad", threshold_points=-1, accrual_multiplier=1.0)

    def test_program_update_date_validation(self):
        today = date.today()
        with pytest.raises(ValueError, match="valid_from must be before valid_until"):
            ProgramUpdate(valid_from=today + timedelta(days=5), valid_until=today)


class TestProgramSettings:
    async def test_create_with_welcome_bonus(
        self, session: AsyncSession, partner_id: UUID
    ):
        p = await service.create_program(
            session, partner_id, _program(welcome_bonus_points=300)
        )
        assert p.welcome_bonus_points == 300

    async def test_create_with_birthday_bonus(
        self, session: AsyncSession, partner_id: UUID
    ):
        p = await service.create_program(
            session,
            partner_id,
            _program(birthday_bonus_points=75, birthday_bonus_days=3),
        )
        assert p.birthday_bonus_points == 75
        assert p.birthday_bonus_days == 3

    async def test_create_with_referral_bonus(
        self, session: AsyncSession, partner_id: UUID
    ):
        p = await service.create_program(
            session, partner_id, _program(referral_bonus_points=150)
        )
        assert p.referral_bonus_points == 150

    async def test_create_with_purchase_restrictions(
        self, session: AsyncSession, partner_id: UUID
    ):
        p = await service.create_program(
            session,
            partner_id,
            _program(min_purchase_amount=50000, max_points_per_transaction=1000),
        )
        assert p.min_purchase_amount == 50000
        assert p.max_points_per_transaction == 1000

    async def test_create_with_redemption_limit(
        self, session: AsyncSession, partner_id: UUID
    ):
        p = await service.create_program(
            session, partner_id, _program(max_redemption_percent=30)
        )
        assert p.max_redemption_percent == 30

    async def test_create_with_validity_period(
        self, session: AsyncSession, partner_id: UUID
    ):
        today = date.today()
        end = today + timedelta(days=90)
        p = await service.create_program(
            session, partner_id, _program(valid_from=today, valid_until=end)
        )
        assert p.valid_from == today
        assert p.valid_until == end

    async def test_create_full_settings(self, session: AsyncSession, partner_id: UUID):
        today = date.today()
        p = await service.create_program(
            session,
            partner_id,
            _program(
                welcome_bonus_points=200,
                birthday_bonus_points=50,
                birthday_bonus_days=7,
                referral_bonus_points=100,
                min_purchase_amount=10000,
                max_points_per_transaction=500,
                max_redemption_percent=50,
                valid_from=today,
                valid_until=today + timedelta(days=365),
            ),
        )
        assert p.welcome_bonus_points == 200
        assert p.birthday_bonus_days == 7
        assert p.referral_bonus_points == 100
        assert p.min_purchase_amount == 10000
        assert p.max_points_per_transaction == 500
        assert p.max_redemption_percent == 50
        assert p.valid_from == today

    async def test_update_adds_welcome_bonus(
        self, session: AsyncSession, partner_id: UUID
    ):
        p = await service.create_program(session, partner_id, _program())
        assert p.welcome_bonus_points is None

        updated = await service.update_program(
            session, p.id, partner_id, ProgramUpdate(welcome_bonus_points=500)
        )
        assert updated.welcome_bonus_points == 500

    async def test_update_clears_birthday_bonus(
        self, session: AsyncSession, partner_id: UUID
    ):
        p = await service.create_program(
            session, partner_id, _program(birthday_bonus_points=100)
        )
        updated = await service.update_program(
            session, p.id, partner_id, ProgramUpdate(birthday_bonus_points=None)
        )
        assert updated.birthday_bonus_points is None

    async def test_update_validity_period(
        self, session: AsyncSession, partner_id: UUID
    ):
        p = await service.create_program(session, partner_id, _program())
        today = date.today()
        end = today + timedelta(days=30)
        updated = await service.update_program(
            session,
            p.id,
            partner_id,
            ProgramUpdate(valid_from=today, valid_until=end),
        )
        assert updated.valid_from == today
        assert updated.valid_until == end

    async def test_default_birthday_bonus_days_is_zero(
        self, session: AsyncSession, partner_id: UUID
    ):
        p = await service.create_program(session, partner_id, _program())
        assert p.birthday_bonus_days == 0

    async def test_none_fields_are_null_by_default(
        self, session: AsyncSession, partner_id: UUID
    ):
        p = await service.create_program(session, partner_id, _program())
        assert p.welcome_bonus_points is None
        assert p.birthday_bonus_points is None
        assert p.referral_bonus_points is None
        assert p.min_purchase_amount is None
        assert p.max_points_per_transaction is None
        assert p.max_redemption_percent is None
        assert p.valid_from is None
        assert p.valid_until is None


class TestProgramTiers:
    async def test_add_tier_returns_updated_program(self, session, program, partner_id):
        result = await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="Бронзовый", threshold_points=0),
        )
        assert len(result.tiers) == 1
        assert result.tiers[0].name == "Бронзовый"
        assert result.tiers[0].threshold_points == 0
        assert result.tiers[0].accrual_multiplier == 1.0

    async def test_add_multiple_tiers_sorted_by_threshold(
        self, session, program, partner_id
    ):
        await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="Золотой", threshold_points=5000),
        )
        await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="Бронзовый", threshold_points=0),
        )
        result = await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="Серебряный", threshold_points=1000),
        )
        thresholds = [t.threshold_points for t in result.tiers]
        assert thresholds == sorted(thresholds)

    async def test_add_tier_with_multiplier(self, session, program, partner_id):
        result = await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="VIP", threshold_points=10000, accrual_multiplier=3.0),
        )
        assert result.tiers[0].accrual_multiplier == 3.0

    async def test_duplicate_name_raises(self, session, program, partner_id):
        await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="Бронзовый", threshold_points=0),
        )
        with pytest.raises(BadRequestError, match="already exists"):
            await service.add_tier(
                session,
                program.id,
                partner_id,
                TierCreate(name="Бронзовый", threshold_points=999),
            )

    async def test_duplicate_threshold_raises(self, session, program, partner_id):
        await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="Бронзовый", threshold_points=0),
        )
        with pytest.raises(BadRequestError, match="already exists"):
            await service.add_tier(
                session,
                program.id,
                partner_id,
                TierCreate(name="Другой", threshold_points=0),
            )

    async def test_update_tier_name(self, session, program, partner_id):
        result = await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="Bronze", threshold_points=0),
        )
        tier_id = result.tiers[0].id

        updated = await service.update_tier(
            session, program.id, tier_id, partner_id, TierUpdate(name="Бронзовый")
        )
        assert updated.tiers[0].name == "Бронзовый"

    async def test_update_tier_multiplier(self, session, program, partner_id):
        result = await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="VIP", threshold_points=5000),
        )
        tier_id = result.tiers[0].id

        updated = await service.update_tier(
            session,
            program.id,
            tier_id,
            partner_id,
            TierUpdate(accrual_multiplier=2.5),
        )
        assert updated.tiers[0].accrual_multiplier == 2.5

    async def test_delete_tier(self, session, program, partner_id):
        result = await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="Bronze", threshold_points=0),
        )
        tier_id = result.tiers[0].id

        final = await service.delete_tier(session, program.id, tier_id, partner_id)
        assert len(final.tiers) == 0

    async def test_delete_one_of_multiple_tiers(self, session, program, partner_id):
        r1 = await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="Бронзовый", threshold_points=0),
        )
        await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="Серебряный", threshold_points=1000),
        )
        bronze_id = r1.tiers[0].id

        final = await service.delete_tier(session, program.id, bronze_id, partner_id)
        assert len(final.tiers) == 1
        assert final.tiers[0].name == "Серебряный"

    async def test_archived_program_cannot_add_tier(self, session, program, partner_id):
        await service.transition_status(
            session, program.id, partner_id, ProgramStatus.ARCHIVED
        )
        with pytest.raises(BadRequestError, match="archived"):
            await service.add_tier(
                session,
                program.id,
                partner_id,
                TierCreate(name="Bronze", threshold_points=0),
            )

    async def test_archived_program_cannot_update_tier(
        self, session, program, partner_id
    ):
        result = await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="Bronze", threshold_points=0),
        )
        tier_id = result.tiers[0].id
        await service.transition_status(
            session, program.id, partner_id, ProgramStatus.ARCHIVED
        )
        with pytest.raises(BadRequestError, match="archived"):
            await service.update_tier(
                session, program.id, tier_id, partner_id, TierUpdate(name="Gold")
            )

    async def test_archived_program_cannot_delete_tier(
        self, session, program, partner_id
    ):
        result = await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="Bronze", threshold_points=0),
        )
        tier_id = result.tiers[0].id
        await service.transition_status(
            session, program.id, partner_id, ProgramStatus.ARCHIVED
        )
        with pytest.raises(BadRequestError, match="archived"):
            await service.delete_tier(session, program.id, tier_id, partner_id)

    async def test_tier_not_found_raises(self, session, program, partner_id):
        with pytest.raises(NotFoundError):
            await service.delete_tier(session, program.id, uuid4(), partner_id)

    async def test_tier_belongs_to_another_program_raises(
        self, session: AsyncSession, partner_id: UUID
    ):
        p1 = await service.create_program(session, partner_id, _program())
        p2 = await service.create_program(
            session, partner_id, _program(name="Программа 2")
        )
        result = await service.add_tier(
            session, p1.id, partner_id, TierCreate(name="Bronze", threshold_points=0)
        )
        tier_id = result.tiers[0].id

        with pytest.raises(ForbiddenError):
            await service.delete_tier(session, p2.id, tier_id, partner_id)

    async def test_new_program_has_empty_tiers(self, program):
        assert program.tiers == []

    async def test_tier_ids_are_unique(self, session, program, partner_id):
        await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="Бронзовый", threshold_points=0),
        )
        result = await service.add_tier(
            session,
            program.id,
            partner_id,
            TierCreate(name="Серебряный", threshold_points=1000),
        )
        ids = [t.id for t in result.tiers]
        assert len(ids) == len(set(ids))
