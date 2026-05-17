"""Сгорание баллов по сроку (TTL) и предупреждение о скором сгорании.

Источник истины по «лотам» баллов — accrual-транзакции с проставленным
`expires_at` (см. points.service.accrue, program.points_ttl_days).

Баланс денормализован одним числом на enrollment, по-лотного учёта нет,
поэтому распределяем уже потраченные баллы по лотам **FIFO** (раньше
начислено — раньше списано):

  spent = Σ(активные accrual-лоты) − points_balance

`spent` — это всё, что ушло с лотов (redemption, прошлые expiration,
reversal). Раскладываем его на лоты от старых к новым; остаток лота —
то, что ещё «висит» на балансе. Сгорают только лоты с истёкшим
`expires_at`, и только их непотраченный остаток.

Джоб идемпотентен: сгоревший accrual помечается `is_reversed=true`
(как при reversal — он перестаёт учитываться в активных лотах),
предупреждение помечается `expiry_warned=true`.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from math import ceil
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.enrollments.models import Enrollment
from app.domains.partners.models import Partner
from app.domains.programs.models import Program
from app.domains.transactions.models import Transaction, TransactionType
from app.events import publisher

logger = logging.getLogger("core.expiration")

# Верхняя граница окна предупреждения (expire_warn_days ≤ 365) —
# грубый предфильтр кандидатов в SQL, точная проверка по лоту в Python.
_MAX_WARN_DAYS = 365


def _naive_utc(dt: datetime) -> datetime:
    """Колонки TIMESTAMP без таймзоны → сравниваем всё в naive UTC."""
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


async def _partner_name(session: AsyncSession, partner_id: UUID) -> str | None:
    partner = await session.get(Partner, partner_id)
    return partner.name if partner else None


async def _candidate_enrollment_ids(
    session: AsyncSession, now: datetime
) -> list[UUID]:
    """Enrollment'ы, где есть истёкший или скоро истекающий активный лот."""
    warn_horizon = now + timedelta(days=_MAX_WARN_DAYS)
    stmt = (
        select(Transaction.enrollment_id)
        .join(Program, Program.id == Transaction.program_id)
        .where(
            Transaction.type == TransactionType.ACCRUAL,
            Transaction.is_reversed.is_(False),
            Transaction.expires_at.is_not(None),
            (
                (Transaction.expires_at <= now)
                | (
                    Transaction.expiry_warned.is_(False)
                    & Program.expire_warn_days.is_not(None)
                    & (Transaction.expires_at <= warn_horizon)
                )
            ),
        )
        .distinct()
    )
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def _process_enrollment(
    session: AsyncSession, enrollment_id: UUID, now: datetime
) -> dict[str, int] | None:
    """Обрабатывает один enrollment в своей транзакции БД.

    Возвращает счётчики (expired_points / warned_points / …) либо None,
    если делать нечего. Публикация событий — после commit.
    """
    enrollment = (
        await session.execute(
            select(Enrollment).where(Enrollment.id == enrollment_id).with_for_update()
        )
    ).scalar_one_or_none()
    if enrollment is None:
        return None

    program = await session.get(Program, enrollment.program_id)
    if program is None:
        return None

    lots = list(
        (
            await session.execute(
                select(Transaction)
                .where(
                    Transaction.enrollment_id == enrollment_id,
                    Transaction.type == TransactionType.ACCRUAL,
                    Transaction.is_reversed.is_(False),
                    Transaction.expires_at.is_not(None),
                )
                .order_by(Transaction.created_at.asc())
            )
        ).scalars()
    )
    # Бессрочные лоты тоже потребляют spent по FIFO — учитываем их в
    # порядке начисления вместе с истекающими.
    all_active = list(
        (
            await session.execute(
                select(Transaction)
                .where(
                    Transaction.enrollment_id == enrollment_id,
                    Transaction.type == TransactionType.ACCRUAL,
                    Transaction.is_reversed.is_(False),
                )
                .order_by(Transaction.created_at.asc())
            )
        ).scalars()
    )
    if not lots:
        return None

    total_active = sum(t.points for t in all_active)
    spent = max(0, total_active - enrollment.points_balance)

    # FIFO-распределение потраченного: считаем непотраченный остаток
    # каждого лота с expires_at.
    remaining: dict[UUID, int] = {}
    rest = spent
    for t in all_active:
        consumed = min(t.points, rest)
        rest -= consumed
        if t.expires_at is not None:
            remaining[t.id] = t.points - consumed

    warn_days = program.expire_warn_days
    warn_threshold = (
        now + timedelta(days=warn_days) if warn_days is not None else None
    )

    expire_amount = 0
    warn_amount = 0
    warn_earliest: datetime | None = None
    customer_id = enrollment.customer_id
    partner_id = program.partner_id

    for t in lots:
        exp = _naive_utc(t.expires_at) if t.expires_at is not None else None
        if exp is None:
            continue
        rem = remaining.get(t.id, 0)
        if exp <= now:
            # Сгорает: гасим непотраченный остаток, лот выводим из учёта.
            expire_amount += rem
            t.is_reversed = True
        elif (
            warn_threshold is not None
            and not t.expiry_warned
            and exp <= warn_threshold
            and rem > 0
        ):
            warn_amount += rem
            t.expiry_warned = True
            if warn_earliest is None or exp < warn_earliest:
                warn_earliest = exp

    if expire_amount == 0 and warn_amount == 0:
        # Возможны лоты с remaining 0, помеченные is_reversed — это
        # валидная чистка, всё равно коммитим.
        await session.commit()
        return None

    expiration_tx: Transaction | None = None
    if expire_amount > 0:
        expiration_tx = Transaction(
            enrollment_id=enrollment.id,
            customer_id=customer_id,
            program_id=program.id,
            partner_id=partner_id,
            type=TransactionType.EXPIRATION,
            points=expire_amount,
            description="Сгорание баллов по сроку действия",
        )
        session.add(expiration_tx)
        enrollment.points_balance -= expire_amount

    await session.commit()

    partner_name = await _partner_name(session, partner_id)

    if expiration_tx is not None:
        await session.refresh(expiration_tx)
        await session.refresh(enrollment)
        await publisher.publish(
            "points.expired",
            {
                "transaction_id": expiration_tx.id,
                "customer_id": customer_id,
                "program_id": program.id,
                "partner_id": partner_id,
                "partner_name": partner_name,
                "points": expire_amount,
                "balance_after": enrollment.points_balance,
                "created_at": expiration_tx.created_at,
            },
            key=str(customer_id),
        )

    if warn_amount > 0 and warn_earliest is not None:
        days_left = max(1, ceil((warn_earliest - now).total_seconds() / 86400))
        await publisher.publish(
            "points.expiring",
            {
                "customer_id": customer_id,
                "program_id": program.id,
                "partner_id": partner_id,
                "partner_name": partner_name,
                "points": warn_amount,
                "days_left": days_left,
            },
            key=str(customer_id),
        )

    return {
        "expired_points": expire_amount,
        "warned_points": warn_amount,
        "expiration_tx": 1 if expiration_tx is not None else 0,
        "warnings": 1 if warn_amount > 0 else 0,
    }


async def run_expiration(
    session: AsyncSession, *, now: datetime | None = None
) -> dict[str, int]:
    """Прогон сгорания/предупреждений по всем enrollment'ам.

    Каждый enrollment обрабатывается в своей транзакции БД, поэтому
    падение одного не откатывает остальные.
    """
    moment = _naive_utc(now or datetime.now(UTC))
    enrollment_ids = await _candidate_enrollment_ids(session, moment)

    totals = {
        "enrollments_scanned": len(enrollment_ids),
        "enrollments_affected": 0,
        "expired_points": 0,
        "expiration_tx": 0,
        "warnings": 0,
        "warned_points": 0,
    }
    for eid in enrollment_ids:
        try:
            res = await _process_enrollment(session, eid, moment)
        except Exception:
            logger.exception("expiration failed for enrollment=%s", eid)
            await session.rollback()
            continue
        if res is None:
            continue
        totals["enrollments_affected"] += 1
        totals["expired_points"] += res["expired_points"]
        totals["expiration_tx"] += res["expiration_tx"]
        totals["warnings"] += res["warnings"]
        totals["warned_points"] += res["warned_points"]

    logger.info("points expiration run: %s", totals)
    return totals
