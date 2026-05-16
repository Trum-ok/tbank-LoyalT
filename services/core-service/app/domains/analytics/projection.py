"""Read-модель аналитики: проекция событий points.* на агрегаты.

Дашборд читает analytics_daily / analytics_heatmap вместо скана
transaction. Наполнение двумя путями:

  * инкрементально — apply_* из inbox-хендлеров (Kafka / /internal/events),
    идемпотентно по analytics_processed_event (at-least-once Kafka);
  * пересборкой из transaction — rebuild_from_transactions(): источник
    истины, backfill и страховка паритета (Kafka может быть выключена
    или событие потеряно — outbox'а нет).

Семантика агрегатов повторяет правила build_partner_analytics:
  * наличие строки в analytics_daily = клиент был активен в этот день
    (любая нереверсная операция);
  * reversal-операции в проекцию не попадают;
  * отмена accrual вычитает начисленные баллы, но активность/чек/heatmap
    исходной операции остаются (как в текущей аналитике);
  * отмена redemption на суммы не влияет (текущая аналитика тоже не
    вычитает reversed redemption).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CursorResult,
    Date,
    Integer,
    Numeric,
    SmallInteger,
    Table,
    Uuid,
    select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base
from app.domains.transactions.models import Transaction, TransactionType


class AnalyticsDaily(Base):
    __tablename__ = "analytics_daily"

    partner_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    accrual_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    accrued_points: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0"
    )
    redeemed_points: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0"
    )
    purchase_amount_sum: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=0, server_default="0"
    )
    purchase_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class AnalyticsHeatmap(Base):
    __tablename__ = "analytics_heatmap"

    partner_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    hour: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    cnt: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class AnalyticsProcessedEvent(Base):
    __tablename__ = "analytics_processed_event"

    event_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(server_default=func.now())


# --------------------------- helpers ---------------------------


def _as_uuid(value: Any) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _as_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _as_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))


async def _mark_processed(session: AsyncSession, event_id: UUID) -> bool:
    """True — событие новое (продолжаем); False — дубль (пропускаем)."""
    stmt = (
        pg_insert(AnalyticsProcessedEvent)
        .values(event_id=event_id)
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    result = cast("CursorResult[Any]", await session.execute(stmt))
    return result.rowcount == 1


async def _bump_daily(
    session: AsyncSession,
    *,
    partner_id: UUID,
    customer_id: UUID,
    day: date,
    accrual_count: int = 0,
    accrued_points: int = 0,
    redeemed_points: int = 0,
    purchase_amount_sum: Decimal | None = None,
    purchase_count: int = 0,
) -> None:
    amount = purchase_amount_sum or Decimal(0)
    values = {
        "partner_id": partner_id,
        "customer_id": customer_id,
        "day": day,
        "accrual_count": accrual_count,
        "accrued_points": accrued_points,
        "redeemed_points": redeemed_points,
        "purchase_amount_sum": amount,
        "purchase_count": purchase_count,
    }
    t = cast(Table, AnalyticsDaily.__table__)
    stmt = (
        pg_insert(t)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["partner_id", "customer_id", "day"],
            set_={
                "accrual_count": t.c.accrual_count + accrual_count,
                "accrued_points": t.c.accrued_points + accrued_points,
                "redeemed_points": t.c.redeemed_points + redeemed_points,
                "purchase_amount_sum": t.c.purchase_amount_sum + amount,
                "purchase_count": t.c.purchase_count + purchase_count,
            },
        )
    )
    await session.execute(stmt)


async def _bump_heatmap(
    session: AsyncSession, partner_id: UUID, when: datetime, delta: int = 1
) -> None:
    t = cast(Table, AnalyticsHeatmap.__table__)
    stmt = (
        pg_insert(t)
        .values(partner_id=partner_id, day=when.date(), hour=when.hour, cnt=delta)
        .on_conflict_do_update(
            index_elements=["partner_id", "day", "hour"],
            set_={"cnt": t.c.cnt + delta},
        )
    )
    await session.execute(stmt)


# --------------------------- incremental apply ---------------------------


async def apply_accrued(session: AsyncSession, payload: dict[str, Any]) -> None:
    event_id = _as_uuid(payload["transaction_id"])
    if not await _mark_processed(session, event_id):
        await session.commit()
        return
    created = _as_dt(payload["created_at"])
    amount = _as_decimal(payload.get("purchase_amount"))
    await _bump_daily(
        session,
        partner_id=_as_uuid(payload["partner_id"]),
        customer_id=_as_uuid(payload["customer_id"]),
        day=created.date(),
        accrual_count=1,
        accrued_points=int(payload["points"]),
        purchase_amount_sum=amount,
        purchase_count=1 if amount is not None else 0,
    )
    await _bump_heatmap(session, _as_uuid(payload["partner_id"]), created)
    await session.commit()


async def apply_redeemed(session: AsyncSession, payload: dict[str, Any]) -> None:
    event_id = _as_uuid(payload["transaction_id"])
    if not await _mark_processed(session, event_id):
        await session.commit()
        return
    created = _as_dt(payload["created_at"])
    await _bump_daily(
        session,
        partner_id=_as_uuid(payload["partner_id"]),
        customer_id=_as_uuid(payload["customer_id"]),
        day=created.date(),
        redeemed_points=int(payload["points"]),
    )
    await _bump_heatmap(session, _as_uuid(payload["partner_id"]), created)
    await session.commit()


async def apply_reversed(session: AsyncSession, payload: dict[str, Any]) -> None:
    # Дедупим по id самой reversal-операции.
    event_id = _as_uuid(payload["transaction_id"])
    if not await _mark_processed(session, event_id):
        await session.commit()
        return
    # Reversal-строка в аналитику не идёт. Корректируем только эффект
    # исходной операции: отмена accrual вычитает начисленные баллы в
    # день исходной транзакции; отмена redemption на суммы не влияет.
    if payload.get("original_type") == TransactionType.ACCRUAL:
        original_created = _as_dt(payload["original_created_at"])
        await _bump_daily(
            session,
            partner_id=_as_uuid(payload["partner_id"]),
            customer_id=_as_uuid(payload["customer_id"]),
            day=original_created.date(),
            accrued_points=-int(payload["points"]),
        )
    await session.commit()


# --------------------------- rebuild from source of truth ---------------------------


async def rebuild_from_transactions(session: AsyncSession) -> dict[str, int]:
    """Полная пересборка проекции из transaction (источник истины).

    Backfill уже накопленных данных и страховка паритета. Пересчёт
    идёт по тем же правилам, что build_partner_analytics, поэтому
    цифры дашборда сходятся с историей независимо от Kafka.
    """
    await session.execute(cast(Table, AnalyticsDaily.__table__).delete())
    await session.execute(cast(Table, AnalyticsHeatmap.__table__).delete())
    await session.execute(cast(Table, AnalyticsProcessedEvent.__table__).delete())

    daily: dict[tuple[UUID, UUID, date], dict[str, Any]] = {}
    heat: dict[tuple[UUID, date, int], int] = {}

    stream = await session.stream(
        select(
            Transaction.partner_id,
            Transaction.customer_id,
            Transaction.type,
            Transaction.points,
            Transaction.purchase_amount,
            Transaction.is_reversed,
            Transaction.created_at,
        )
    )
    async for pid, cid, ttype, points, amount, is_reversed, created in stream:
        if ttype == TransactionType.REVERSAL:
            continue
        d = created.date()
        row = daily.setdefault(
            (pid, cid, d),
            {
                "accrual_count": 0,
                "accrued_points": 0,
                "redeemed_points": 0,
                "purchase_amount_sum": Decimal(0),
                "purchase_count": 0,
            },
        )
        if ttype == TransactionType.ACCRUAL:
            row["accrual_count"] += 1
            if not is_reversed:
                row["accrued_points"] += points
            if amount is not None:
                row["purchase_amount_sum"] += amount
                row["purchase_count"] += 1
        elif ttype == TransactionType.REDEMPTION:
            row["redeemed_points"] += points
        heat[(pid, d, created.hour)] = heat.get((pid, d, created.hour), 0) + 1

    if daily:
        await session.execute(
            cast(Table, AnalyticsDaily.__table__).insert(),
            [
                {
                    "partner_id": pid,
                    "customer_id": cid,
                    "day": d,
                    **vals,
                }
                for (pid, cid, d), vals in daily.items()
            ],
        )
    if heat:
        await session.execute(
            cast(Table, AnalyticsHeatmap.__table__).insert(),
            [
                {"partner_id": pid, "day": d, "hour": h, "cnt": c}
                for (pid, d, h), c in heat.items()
            ],
        )
    await session.commit()
    return {"daily_rows": len(daily), "heatmap_rows": len(heat)}
