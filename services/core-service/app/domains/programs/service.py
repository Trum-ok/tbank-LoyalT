from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.partners.models import Partner
from app.domains.programs.models import Program, ProgramStatus
from app.domains.programs.schemas import ProgramCreate, ProgramUpdate
from app.errors import BadRequestError, ForbiddenError, NotFoundError


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
    await session.refresh(program)
    return program


async def get_program(session: AsyncSession, program_id: UUID) -> Program:
    program = await session.get(Program, program_id)
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
    await session.commit()
    await session.refresh(program)
    return program


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
    await session.refresh(program)
    return program
