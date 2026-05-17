import sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

SERVICE_ROOT = Path(__file__).parents[2] / "services" / "core-service"
sys.path.insert(0, str(SERVICE_ROOT))

from app.domains.points import service as points  # noqa: E402
from app.domains.points.schemas import AccrueRequest, RedeemRequest  # noqa: E402
from app.domains.programs import service as program_service  # noqa: E402
from app.domains.programs.models import ProgramStatus  # noqa: E402
from app.domains.rewards import service as rewards  # noqa: E402
from app.domains.rewards.models import RewardType  # noqa: E402
from app.domains.rewards.schemas import RewardCreate  # noqa: E402
from app.errors import ConflictError  # noqa: E402


@pytest.fixture
def customer_id() -> UUID:
    return uuid4()


async def _publish(session: AsyncSession, program, partner_id: UUID) -> None:
    await program_service.transition_status(
        session, program.id, partner_id, ProgramStatus.PUBLISHED
    )


class TestAccrueIdempotency:
    async def test_same_key_does_not_double_balance(
        self, session, program, partner_id, customer_id
    ):
        await _publish(session, program, partner_id)
        req = AccrueRequest(
            customer_id=customer_id,
            program_id=program.id,
            purchase_amount=Decimal("1000.00"),
        )

        tx1, bal1, _ = await points.accrue(session, partner_id, req, "key-1")
        tx2, bal2, _ = await points.accrue(session, partner_id, req, "key-1")

        assert tx1.id == tx2.id
        assert bal1 == bal2 == 50  # 5% от 1000

    async def test_different_keys_create_two_transactions(
        self, session, program, partner_id, customer_id
    ):
        await _publish(session, program, partner_id)
        req = AccrueRequest(
            customer_id=customer_id,
            program_id=program.id,
            purchase_amount=Decimal("1000.00"),
        )

        tx1, _, _ = await points.accrue(session, partner_id, req, "key-a")
        tx2, bal2, _ = await points.accrue(session, partner_id, req, "key-b")

        assert tx1.id != tx2.id
        assert bal2 == 100

    async def test_same_key_different_body_conflict(
        self, session, program, partner_id, customer_id
    ):
        await _publish(session, program, partner_id)
        await points.accrue(
            session,
            partner_id,
            AccrueRequest(
                customer_id=customer_id,
                program_id=program.id,
                purchase_amount=Decimal("1000.00"),
            ),
            "key-x",
        )

        with pytest.raises(ConflictError, match="different request"):
            await points.accrue(
                session,
                partner_id,
                AccrueRequest(
                    customer_id=customer_id,
                    program_id=program.id,
                    purchase_amount=Decimal("2000.00"),
                ),
                "key-x",
            )

    async def test_replay_returns_stored_transaction_fields(
        self, session, program, partner_id, customer_id
    ):
        await _publish(session, program, partner_id)
        req = AccrueRequest(customer_id=customer_id, program_id=program.id, points=42)
        original, _, _ = await points.accrue(session, partner_id, req, "key-r")
        replayed, _, _ = await points.accrue(session, partner_id, req, "key-r")

        assert replayed.id == original.id
        assert replayed.points == 42
        assert replayed.idempotency_key == "key-r"


class TestRedeemIdempotency:
    async def test_same_key_does_not_double_debit(
        self, session, program, partner_id, customer_id
    ):
        await _publish(session, program, partner_id)
        await points.accrue(
            session,
            partner_id,
            AccrueRequest(customer_id=customer_id, program_id=program.id, points=500),
            "accrue-key",
        )
        reward = await rewards.create_reward(
            session,
            partner_id,
            program.id,
            RewardCreate(title="Кофе", cost_points=100, type=RewardType.FREE_ITEM),
        )
        req = RedeemRequest(
            customer_id=customer_id, program_id=program.id, reward_id=reward.id
        )

        tx1, bal1, _ = await points.redeem(session, partner_id, req, "redeem-1")
        tx2, bal2, _ = await points.redeem(session, partner_id, req, "redeem-1")

        assert tx1.id == tx2.id
        assert bal1 == bal2 == 400  # списано один раз

    async def test_redeem_same_key_different_reward_conflict(
        self, session, program, partner_id, customer_id
    ):
        await _publish(session, program, partner_id)
        await points.accrue(
            session,
            partner_id,
            AccrueRequest(customer_id=customer_id, program_id=program.id, points=500),
            "accrue-key",
        )
        r1 = await rewards.create_reward(
            session,
            partner_id,
            program.id,
            RewardCreate(title="A", cost_points=100, type=RewardType.FREE_ITEM),
        )
        r2 = await rewards.create_reward(
            session,
            partner_id,
            program.id,
            RewardCreate(title="B", cost_points=100, type=RewardType.FREE_ITEM),
        )
        await points.redeem(
            session,
            partner_id,
            RedeemRequest(
                customer_id=customer_id, program_id=program.id, reward_id=r1.id
            ),
            "rk",
        )

        with pytest.raises(ConflictError, match="different request"):
            await points.redeem(
                session,
                partner_id,
                RedeemRequest(
                    customer_id=customer_id,
                    program_id=program.id,
                    reward_id=r2.id,
                ),
                "rk",
            )
