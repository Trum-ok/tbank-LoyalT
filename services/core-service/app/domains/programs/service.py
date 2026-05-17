from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.partners.models import Partner
from app.domains.programs.models import Program, ProgramStatus, ProgramTier
from app.domains.programs.schemas import (
    ProgramCreate,
    ProgramUpdate,
    TierCreate,
    TierUpdate,
    _validate_expire_warn,
)
from app.errors import BadRequestError, ForbiddenError, NotFoundError


def get_current_tier(
    points_balance: int, tiers: list[ProgramTier]
) -> ProgramTier | None:
    """Возвращает наивысший тир, порог которого не превышает points_balance."""
    eligible = [t for t in tiers if t.threshold_points <= points_balance]
    return max(eligible, key=lambda t: t.threshold_points) if eligible else None


async def create_program(
    session: AsyncSession, partner_id: UUID, data: ProgramCreate
) -> Program:
    # Партнёр должен существовать в локальной реплике core-service — иначе
    # FK-violation превратится в 500 с потерей CORS-заголовков.
    if await session.get(Partner, partner_id) is None:
        raise NotFoundError("Partner not found")

    program = Program(partner_id=partner_id, **data.model_dump())
    session.add(program)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise NotFoundError("Partner not found") from exc
    return await get_program(session, program.id)


async def get_program(session: AsyncSession, program_id: UUID) -> Program:
    result = await session.execute(
        select(Program)
        .where(Program.id == program_id)
        .options(selectinload(Program.tiers))
        .execution_options(populate_existing=True)
    )
    program = result.scalar_one_or_none()
    if program is None:
        raise NotFoundError("Program not found")
    return program


async def get_program_for_partner(
    session: AsyncSession, program_id: UUID, partner_id: UUID
) -> Program:
    program = await get_program(session, program_id)
    if program.partner_id != partner_id:
        raise ForbiddenError("Program belongs to another partner")
    return program


async def list_programs_for_partner(
    session: AsyncSession, partner_id: UUID
) -> list[Program]:
    result = await session.execute(
        select(Program)
        .where(Program.partner_id == partner_id)
        .options(selectinload(Program.tiers))
        .order_by(Program.created_at.desc())
    )
    return list(result.scalars().all())


async def update_program(
    session: AsyncSession, program_id: UUID, partner_id: UUID, data: ProgramUpdate
) -> Program:
    program = await get_program_for_partner(session, program_id, partner_id)
    if program.status == ProgramStatus.ARCHIVED:
        raise BadRequestError("Archived program cannot be updated")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(program, field, value)
    # Кросс-валидация против итогового состояния: патч мог изменить
    # только одно из полей (TTL / предупреждение).
    try:
        _validate_expire_warn(program.points_ttl_days, program.expire_warn_days)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc
    await session.commit()
    return await get_program(session, program.id)


async def transition_status(
    session: AsyncSession,
    program_id: UUID,
    partner_id: UUID,
    target: ProgramStatus,
) -> Program:
    program = await get_program_for_partner(session, program_id, partner_id)
    if program.status == target:
        return program

    allowed: dict[ProgramStatus, set[ProgramStatus]] = {
        ProgramStatus.DRAFT: {ProgramStatus.PUBLISHED, ProgramStatus.ARCHIVED},
        ProgramStatus.PUBLISHED: {ProgramStatus.PAUSED, ProgramStatus.ARCHIVED},
        ProgramStatus.PAUSED: {ProgramStatus.PUBLISHED, ProgramStatus.ARCHIVED},
        ProgramStatus.ARCHIVED: set(),
    }
    if target not in allowed[program.status]:
        raise BadRequestError(
            f"Cannot transition program from {program.status} to {target}"
        )
    program.status = target
    await session.commit()
    return await get_program(session, program.id)


# ---------------------------------------------------------------------------
# Tier operations
# ---------------------------------------------------------------------------


async def _get_tier(session: AsyncSession, tier_id: UUID) -> ProgramTier:
    tier = await session.get(ProgramTier, tier_id)
    if tier is None:
        raise NotFoundError("Tier not found")
    return tier


async def add_tier(
    session: AsyncSession,
    program_id: UUID,
    partner_id: UUID,
    data: TierCreate,
) -> Program:
    program = await get_program_for_partner(session, program_id, partner_id)
    if program.status == ProgramStatus.ARCHIVED:
        raise BadRequestError("Cannot add tiers to an archived program")

    tier = ProgramTier(program_id=program_id, **data.model_dump())
    session.add(tier)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise BadRequestError(
            "Tier with this name or threshold already exists in the program"
        ) from exc
    session.expire(program)
    return await get_program(session, program_id)


async def update_tier(
    session: AsyncSession,
    program_id: UUID,
    tier_id: UUID,
    partner_id: UUID,
    data: TierUpdate,
) -> Program:
    program = await get_program_for_partner(session, program_id, partner_id)
    if program.status == ProgramStatus.ARCHIVED:
        raise BadRequestError("Cannot update tiers of an archived program")

    tier = await _get_tier(session, tier_id)
    if tier.program_id != program_id:
        raise ForbiddenError("Tier does not belong to this program")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tier, field, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise BadRequestError(
            "Tier with this name or threshold already exists in the program"
        ) from exc
    session.expire(program)
    return await get_program(session, program_id)


async def delete_tier(
    session: AsyncSession,
    program_id: UUID,
    tier_id: UUID,
    partner_id: UUID,
) -> Program:
    program = await get_program_for_partner(session, program_id, partner_id)
    if program.status == ProgramStatus.ARCHIVED:
        raise BadRequestError("Cannot delete tiers of an archived program")

    tier = await _get_tier(session, tier_id)
    if tier.program_id != program_id:
        raise ForbiddenError("Tier does not belong to this program")

    await session.delete(tier)
    await session.commit()
    session.expire(program)
    return await get_program(session, program_id)
