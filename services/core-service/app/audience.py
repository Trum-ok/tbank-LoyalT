"""Разрешение аудитории рассылки по сегменту.

Используется internal-эндпоинтом: partner-service спрашивает у core-service
список customer_id для выбранного сегмента (PII в core нет — только UUID).
"""

from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.enrollments.models import Enrollment
from app.domains.programs.models import Program
from app.domains.transactions.models import Transaction, TransactionType


class AudienceSegment(StrEnum):
    ALL_ENROLLED = "all_enrolled"  # все с активным enrollment у партнёра
    ACTIVE_30D = "active_30d"  # есть операция за последние 30 дней
    BY_PROGRAM = "by_program"  # подключённые к конкретной программе
    BALANCE_POSITIVE = "balance_positive"  # есть ненулевой баланс
    NEW_7D = "new_7d"  # вступили за последние 7 дней


async def resolve_audience(
    session: AsyncSession,
    partner_id: UUID,
    segment: AudienceSegment,
    program_id: UUID | None = None,
) -> list[UUID]:
    """Возвращает список уникальных customer_id для сегмента."""
    base = (
        select(Enrollment.customer_id)
        .join(Program, Program.id == Enrollment.program_id)
        .where(
            Program.partner_id == partner_id,
            Enrollment.is_archived.is_(False),
        )
        .distinct()
    )

    if segment == AudienceSegment.BY_PROGRAM:
        if program_id is None:
            return []
        stmt = base.where(Enrollment.program_id == program_id)
    elif segment == AudienceSegment.BALANCE_POSITIVE:
        stmt = base.where(Enrollment.points_balance > 0)
    elif segment == AudienceSegment.NEW_7D:
        since = datetime.utcnow() - timedelta(days=7)
        stmt = base.where(Enrollment.created_at >= since)
    elif segment == AudienceSegment.ACTIVE_30D:
        since = datetime.utcnow() - timedelta(days=30)
        active_subq = (
            select(Transaction.customer_id)
            .where(
                Transaction.partner_id == partner_id,
                Transaction.created_at >= since,
                Transaction.type != TransactionType.REVERSAL,
            )
            .distinct()
        )
        stmt = base.where(Enrollment.customer_id.in_(active_subq))
    else:  # ALL_ENROLLED
        stmt = base

    result = await session.execute(stmt)
    return list(result.scalars().all())
