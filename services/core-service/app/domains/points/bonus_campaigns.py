"""Воркер бонусных кампаний.

Запускается ежедневно. Обходит все активные BonusTrigger и начисляет
баллы подходящим enrollment'ам.

Типы кампаний:
  birthday    — клиент, у которого (today + days_before) совпадает с ДР
                по месяцу/дню
  fixed_date  — fire_date == today; если repeat_yearly — сравниваем (month, day)
  interval    — N дней после даты enrollment:
                  repeat=False  → ровно на N-й день
                  repeat=True   → каждые N дней (дней от старта % N == 0)
  inactivity  — нет транзакций (не ACCRUAL типа BONUS/кампании) за
                interval_days дней
  manual      — не обрабатывается воркером (только /fire)

Идемпотентность обеспечивается проверкой BonusTriggerLog: если запись
за сегодня уже есть — пропускаем.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.enrollments.models import Customer, Enrollment
from app.domains.enrollments.service import add_points_balance
from app.domains.programs.models import (
    BonusTrigger,
    BonusTriggerLog,
    Program,
    TriggerType,
)
from app.domains.transactions.models import Transaction, TransactionType

logger = logging.getLogger("core.bonus_campaigns")


def _today_utc() -> date:
    return datetime.now(UTC).date()


def _naive_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _already_fired_today(
    session: AsyncSession, trigger_id: UUID, enrollment_id: UUID, today: date
) -> bool:
    """Проверяет, было ли срабатывание сегодня."""
    start = datetime(today.year, today.month, today.day, 0, 0, 0)
    end = start + timedelta(days=1)
    result = await session.execute(
        select(BonusTriggerLog).where(
            BonusTriggerLog.trigger_id == trigger_id,
            BonusTriggerLog.enrollment_id == enrollment_id,
            BonusTriggerLog.fired_at >= start,
            BonusTriggerLog.fired_at < end,
        )
    )
    return result.scalar_one_or_none() is not None


async def _already_fired_in_window(
    session: AsyncSession,
    trigger_id: UUID,
    enrollment_id: UUID,
    window_days: int,
    today: date,
) -> bool:
    """Проверяет, было ли срабатывание за последние window_days дней."""
    since = datetime(today.year, today.month, today.day, 0, 0, 0) - timedelta(
        days=window_days - 1
    )
    result = await session.execute(
        select(BonusTriggerLog).where(
            BonusTriggerLog.trigger_id == trigger_id,
            BonusTriggerLog.enrollment_id == enrollment_id,
            BonusTriggerLog.fired_at >= since,
        )
    )
    return result.scalar_one_or_none() is not None


async def _accrue(
    session: AsyncSession,
    trigger: BonusTrigger,
    enrollment: Enrollment,
    program: Program,
    today: date,
) -> None:
    """Начисляет баллы и создаёт лог."""
    tx = Transaction(
        enrollment_id=enrollment.id,
        customer_id=enrollment.customer_id,
        program_id=program.id,
        partner_id=program.partner_id,
        type=TransactionType.ACCRUAL,
        points=trigger.points,
        description=f"Кампания: {trigger.name}",
    )
    session.add(tx)
    await add_points_balance(session, enrollment.id, trigger.points)

    log = BonusTriggerLog(
        trigger_id=trigger.id,
        enrollment_id=enrollment.id,
        fired_at=datetime(today.year, today.month, today.day, 0, 0, 0),
    )
    session.add(log)


async def _process_trigger(
    session: AsyncSession,
    trigger: BonusTrigger,
    today: date,
) -> int:
    """Обрабатывает один триггер. Возвращает кол-во начислений."""
    if trigger.type == TriggerType.MANUAL:
        return 0

    program = await session.get(Program, trigger.program_id)
    if program is None:
        return 0

    # Активные enrollment'ы программы
    enrollments_result = await session.execute(
        select(Enrollment).where(
            Enrollment.program_id == trigger.program_id,
            Enrollment.is_archived.is_(False),
        )
    )
    enrollments = list(enrollments_result.scalars())

    count = 0

    for enrollment in enrollments:
        try:
            fired = await _check_and_fire(session, trigger, enrollment, program, today)
            if fired:
                count += 1
        except Exception:
            logger.exception(
                "bonus_campaigns: error for trigger=%s enrollment=%s",
                trigger.id,
                enrollment.id,
            )
            await session.rollback()
            continue

    if count > 0:
        try:
            await session.commit()
        except Exception:
            logger.exception(
                "bonus_campaigns: commit failed for trigger=%s", trigger.id
            )
            await session.rollback()
            return 0

    return count


async def _check_and_fire(
    session: AsyncSession,
    trigger: BonusTrigger,
    enrollment: Enrollment,
    program: Program,
    today: date,
) -> bool:
    """Проверяет условие и начисляет баллы если нужно. Возвращает True при начислении."""
    t_type = TriggerType(trigger.type)

    if t_type == TriggerType.BIRTHDAY:
        customer = await session.get(Customer, enrollment.customer_id)
        if customer is None or customer.birthday is None:
            return False

        days_before = trigger.days_before or 0
        target_date = customer.birthday.replace(year=today.year)
        # Учитываем переход года для ДР в конце декабря
        fire_on = target_date - timedelta(days=days_before)
        # Если дата уже прошла в этом году, смотрим следующий
        if target_date < today:
            try:
                target_date = customer.birthday.replace(year=today.year + 1)
                fire_on = target_date - timedelta(days=days_before)
            except ValueError:
                # 29 февраля — пропускаем
                return False

        if fire_on != today:
            return False

        if await _already_fired_today(session, trigger.id, enrollment.id, today):
            return False

        await _accrue(session, trigger, enrollment, program, today)
        return True

    elif t_type == TriggerType.FIXED_DATE:
        if trigger.fire_date is None:
            return False

        if trigger.repeat_yearly:
            matches = (
                trigger.fire_date.month == today.month
                and trigger.fire_date.day == today.day
            )
        else:
            matches = trigger.fire_date == today

        if not matches:
            return False

        if await _already_fired_today(session, trigger.id, enrollment.id, today):
            return False

        await _accrue(session, trigger, enrollment, program, today)
        return True

    elif t_type == TriggerType.INTERVAL:
        if trigger.interval_days is None or trigger.interval_days <= 0:
            return False

        enrollment_date = (
            enrollment.created_at.date()
            if hasattr(enrollment.created_at, "date")
            else enrollment.created_at
        )
        days_since = (today - enrollment_date).days

        if trigger.repeat_interval:
            if days_since <= 0 or days_since % trigger.interval_days != 0:
                return False
        else:
            if days_since != trigger.interval_days:
                return False

        if await _already_fired_today(session, trigger.id, enrollment.id, today):
            return False

        await _accrue(session, trigger, enrollment, program, today)
        return True

    elif t_type == TriggerType.INACTIVITY:
        if trigger.interval_days is None or trigger.interval_days <= 0:
            return False

        # Нет транзакций за последние interval_days дней
        cutoff = datetime(today.year, today.month, today.day, 0, 0, 0) - timedelta(
            days=trigger.interval_days
        )
        tx_result = await session.execute(
            select(Transaction).where(
                Transaction.enrollment_id == enrollment.id,
                Transaction.created_at >= cutoff,
            )
        )
        recent_tx = tx_result.scalar_one_or_none()
        if recent_tx is not None:
            return False

        # Нет лога за последние interval_days дней
        if await _already_fired_in_window(
            session, trigger.id, enrollment.id, trigger.interval_days, today
        ):
            return False

        await _accrue(session, trigger, enrollment, program, today)
        return True

    return False


async def run_bonus_campaigns(
    session: AsyncSession, *, today: date | None = None
) -> int:
    """Прогон всех активных бонусных кампаний. Возвращает количество начислений."""
    run_date = today or _today_utc()

    triggers_result = await session.execute(
        select(BonusTrigger).where(
            BonusTrigger.is_active.is_(True),
            BonusTrigger.type != TriggerType.MANUAL,
        )
    )
    triggers = list(triggers_result.scalars())

    total = 0
    for trigger in triggers:
        try:
            n = await _process_trigger(session, trigger, run_date)
            total += n
        except Exception:
            logger.exception(
                "bonus_campaigns: unexpected error for trigger=%s", trigger.id
            )
            await session.rollback()
            continue

    logger.info("bonus_campaigns run: date=%s total_accruals=%d", run_date, total)
    return total
