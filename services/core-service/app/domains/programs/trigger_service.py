"""Сервис бонусных кампаний (BonusTrigger)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.enrollments.models import Enrollment
from app.domains.programs.models import BonusTrigger, BonusTriggerLog, Program
from app.domains.programs.trigger_schemas import (
    BonusTriggerCreate,
    BonusTriggerUpdate,
    TriggerType,
)
from app.domains.transactions.models import Transaction, TransactionType
from app.errors import BadRequestError, ForbiddenError, NotFoundError


async def _get_program_for_partner(
    session: AsyncSession, program_id: UUID, partner_id: UUID
) -> Program:
    program = await session.get(Program, program_id)
    if program is None:
        raise NotFoundError("Program not found")
    if program.partner_id != partner_id:
        raise ForbiddenError("Access denied")
    return program


async def list_triggers(session: AsyncSession, program_id: UUID) -> list[BonusTrigger]:
    result = await session.execute(
        select(BonusTrigger)
        .where(BonusTrigger.program_id == program_id)
        .order_by(BonusTrigger.created_at)
    )
    return list(result.scalars())


async def create_trigger(
    session: AsyncSession,
    program_id: UUID,
    partner_id: UUID,
    data: BonusTriggerCreate,
) -> BonusTrigger:
    await _get_program_for_partner(session, program_id, partner_id)

    trigger = BonusTrigger(
        program_id=program_id,
        **data.model_dump(),
    )
    session.add(trigger)
    await session.commit()
    await session.refresh(trigger)
    return trigger


async def update_trigger(
    session: AsyncSession,
    program_id: UUID,
    trigger_id: UUID,
    partner_id: UUID,
    data: BonusTriggerUpdate,
) -> BonusTrigger:
    await _get_program_for_partner(session, program_id, partner_id)

    trigger = await session.get(BonusTrigger, trigger_id)
    if trigger is None or trigger.program_id != program_id:
        raise NotFoundError("Trigger not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(trigger, field, value)
    trigger.updated_at = datetime.now(UTC).replace(tzinfo=None)

    await session.commit()
    await session.refresh(trigger)
    return trigger


async def delete_trigger(
    session: AsyncSession,
    program_id: UUID,
    trigger_id: UUID,
    partner_id: UUID,
) -> None:
    await _get_program_for_partner(session, program_id, partner_id)

    trigger = await session.get(BonusTrigger, trigger_id)
    if trigger is None or trigger.program_id != program_id:
        raise NotFoundError("Trigger not found")

    await session.delete(trigger)
    await session.commit()


async def fire_trigger(
    session: AsyncSession,
    trigger_id: UUID,
    program_id: UUID,
    partner_id: UUID,
) -> int:
    """Ручной запуск MANUAL-кампании. Возвращает кол-во начислений."""
    await _get_program_for_partner(session, program_id, partner_id)

    trigger = await session.get(BonusTrigger, trigger_id)
    if trigger is None or trigger.program_id != program_id:
        raise NotFoundError("Trigger not found")

    if trigger.type != TriggerType.MANUAL:
        raise BadRequestError("Only MANUAL triggers can be fired manually")

    # Активные enrollment'ы программы
    result = await session.execute(
        select(Enrollment).where(
            Enrollment.program_id == program_id,
            Enrollment.is_archived.is_(False),
        )
    )
    enrollments = list(result.scalars())

    count = 0
    program = await session.get(Program, program_id)
    if program is None:
        raise NotFoundError("Program not found")

    for enrollment in enrollments:
        tx = Transaction(
            enrollment_id=enrollment.id,
            customer_id=enrollment.customer_id,
            program_id=program_id,
            partner_id=partner_id,
            type=TransactionType.ACCRUAL,
            points=trigger.points,
            description=f"Кампания: {trigger.name}",
        )
        session.add(tx)
        enrollment.points_balance += trigger.points

        log = BonusTriggerLog(
            trigger_id=trigger.id,
            enrollment_id=enrollment.id,
        )
        session.add(log)
        count += 1

    await session.commit()
    return count
