from datetime import UTC, datetime, timedelta
from decimal import ROUND_FLOOR, Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.enrollments.models import Enrollment
from app.domains.enrollments.service import (
    ensure_customer,
    get_enrollment_by_pair,
)
from app.domains.points.schemas import AccrueRequest, RedeemRequest
from app.domains.programs.models import Program, ProgramStatus, ProgramType
from app.domains.programs.service import get_program
from app.domains.rewards.service import get_reward
from app.domains.transactions.models import Transaction, TransactionType
from app.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError


def _calculate_points(program: Program, req: AccrueRequest) -> int:
    """Считает, сколько баллов начислить по заявке партнёра."""
    if req.points is not None:
        return req.points

    rule = program.accrual_rule or {}
    if program.type == ProgramType.ACCRUAL:
        if req.purchase_amount is None:
            raise BadRequestError("purchase_amount is required for accrual program")
        if "percent" in rule:
            percent = Decimal(str(rule["percent"]))
            points = (req.purchase_amount * percent / Decimal("100")).quantize(
                Decimal("1"), rounding=ROUND_FLOOR
            )
            return int(points)
        if "points_per_rub" in rule:
            ppr = Decimal(str(rule["points_per_rub"]))
            points = (req.purchase_amount * ppr).quantize(
                Decimal("1"), rounding=ROUND_FLOOR
            )
            return int(points)
        raise BadRequestError("Program accrual rule is misconfigured")

    if program.type == ProgramType.VISIT:
        visits = req.visits or 1
        per_visit = int(rule.get("points_per_visit", 0))
        if per_visit <= 0:
            raise BadRequestError("Program accrual rule is misconfigured")
        return visits * per_visit

    if program.type == ProgramType.STAMPS:
        # 1 штамп = 1 балл; награда выдаётся после `visits_required` штампов
        # отдельным reward (списанием).
        return req.visits or 1

    raise BadRequestError(f"Unsupported program type: {program.type}")


async def _lock_enrollment(
    session: AsyncSession, customer_id: UUID, program_id: UUID
) -> Enrollment:
    stmt = (
        select(Enrollment)
        .where(
            Enrollment.customer_id == customer_id,
            Enrollment.program_id == program_id,
        )
        .with_for_update()
    )
    result = await session.execute(stmt)
    enrollment = result.scalar_one_or_none()
    if enrollment is None:
        raise NotFoundError("Customer is not enrolled in this program")
    return enrollment


async def accrue(
    session: AsyncSession, partner_id: UUID, req: AccrueRequest
) -> tuple[Transaction, int]:
    program = await get_program(session, req.program_id)
    if program.partner_id != partner_id:
        raise ForbiddenError("Program belongs to another partner")
    if program.status != ProgramStatus.PUBLISHED:
        raise BadRequestError("Program is not active")

    points = _calculate_points(program, req)
    if points <= 0:
        raise BadRequestError("Calculated points is non-positive")

    await ensure_customer(session, req.customer_id)
    # Авто-подключение клиента к программе, если он не подключён.
    try:
        enrollment = await get_enrollment_by_pair(session, req.customer_id, req.program_id)
    except NotFoundError:
        enrollment = Enrollment(customer_id=req.customer_id, program_id=req.program_id)
        session.add(enrollment)
        await session.flush()

    enrollment = await _lock_enrollment(session, req.customer_id, req.program_id)

    expires_at: datetime | None = None
    if program.points_ttl_days:
        expires_at = datetime.now(UTC) + timedelta(days=program.points_ttl_days)

    transaction = Transaction(
        enrollment_id=enrollment.id,
        customer_id=req.customer_id,
        program_id=req.program_id,
        partner_id=partner_id,
        type=TransactionType.ACCRUAL,
        points=points,
        purchase_amount=req.purchase_amount,
        expires_at=expires_at,
        description=req.description,
    )
    session.add(transaction)
    enrollment.points_balance += points
    await session.commit()
    await session.refresh(transaction)
    await session.refresh(enrollment)
    return transaction, enrollment.points_balance


async def redeem(
    session: AsyncSession, partner_id: UUID, req: RedeemRequest
) -> tuple[Transaction, int]:
    program = await get_program(session, req.program_id)
    if program.partner_id != partner_id:
        raise ForbiddenError("Program belongs to another partner")
    if program.status != ProgramStatus.PUBLISHED:
        raise BadRequestError("Program is not active")

    reward = await get_reward(session, req.reward_id)
    if reward.program_id != req.program_id:
        raise BadRequestError("Reward does not belong to this program")
    if not reward.is_active:
        raise BadRequestError("Reward is not active")

    enrollment = await _lock_enrollment(session, req.customer_id, req.program_id)

    if reward.cost_points < program.min_redemption:
        raise BadRequestError("Reward cost is below program min_redemption threshold")
    if enrollment.points_balance < reward.cost_points:
        raise ConflictError("Insufficient points balance")

    transaction = Transaction(
        enrollment_id=enrollment.id,
        customer_id=req.customer_id,
        program_id=req.program_id,
        partner_id=partner_id,
        type=TransactionType.REDEMPTION,
        points=reward.cost_points,
        reward_id=reward.id,
        description=req.description or reward.title,
    )
    session.add(transaction)
    enrollment.points_balance -= reward.cost_points
    await session.commit()
    await session.refresh(transaction)
    await session.refresh(enrollment)
    return transaction, enrollment.points_balance


async def reverse(
    session: AsyncSession,
    partner_id: UUID,
    transaction_id: UUID,
    description: str | None = None,
) -> tuple[Transaction, int]:
    original = await session.get(Transaction, transaction_id)
    if original is None:
        raise NotFoundError("Transaction not found")
    if original.partner_id != partner_id:
        raise ForbiddenError("Transaction belongs to another partner")
    if original.type == TransactionType.REVERSAL:
        raise BadRequestError("Cannot reverse a reversal")
    if original.is_reversed:
        raise BadRequestError("Transaction is already reversed")

    enrollment = await _lock_enrollment(
        session, original.customer_id, original.program_id
    )

    # Знак: отменяем эффект исходной транзакции на балансе.
    # accrual: balance -= points; redemption: balance += points
    if original.type == TransactionType.ACCRUAL:
        if enrollment.points_balance < original.points:
            raise ConflictError(
                "Cannot reverse accrual: client has already spent these points"
            )
        delta = -original.points
    elif original.type == TransactionType.REDEMPTION:
        delta = original.points
    elif original.type == TransactionType.EXPIRATION:
        delta = original.points
    else:
        raise BadRequestError("Unsupported original transaction type")

    reversal = Transaction(
        enrollment_id=enrollment.id,
        customer_id=original.customer_id,
        program_id=original.program_id,
        partner_id=partner_id,
        type=TransactionType.REVERSAL,
        points=original.points,
        reverses_id=original.id,
        description=description or f"Reversal of {original.id}",
    )
    session.add(reversal)
    original.is_reversed = True
    enrollment.points_balance += delta
    await session.commit()
    await session.refresh(reversal)
    await session.refresh(enrollment)
    return reversal, enrollment.points_balance


async def get_balance(
    session: AsyncSession, customer_id: UUID, program_id: UUID
) -> Enrollment:
    return await get_enrollment_by_pair(session, customer_id, program_id)


async def list_balances(session: AsyncSession, customer_id: UUID) -> list[Enrollment]:
    stmt = (
        select(Enrollment)
        .where(
            Enrollment.customer_id == customer_id,
            Enrollment.is_archived.is_(False),
        )
        .order_by(Enrollment.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
