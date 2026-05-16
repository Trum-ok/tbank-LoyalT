"""Read-only метрики по схемам соседних сервисов.

Используем сырой SQL через `text()` — это даёт явный контракт читаемых
таблиц и не требует синхронизации SQLAlchemy-моделей с core/partner.
Источники:
  - core.partner, core.customer, core.enrollment, core.transaction
  - partner.application
"""

from datetime import date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domains.metrics.schemas import (
    CustomersOverview,
    DailyCount,
    PartnersOverview,
    PlatformOverview,
    TopPartner,
    TransactionsOverview,
)

settings = get_settings()
CORE = settings.core_schema
PARTNER = settings.partner_schema


async def partners_overview(session: AsyncSession) -> PartnersOverview:
    rows_status = (
        await session.execute(
            text(f"SELECT status, COUNT(*) FROM {CORE}.partner GROUP BY status")
        )
    ).all()
    rows_category = (
        await session.execute(
            text(f"SELECT category, COUNT(*) FROM {CORE}.partner GROUP BY category")
        )
    ).all()
    pending = (
        await session.execute(
            text(f"SELECT COUNT(*) FROM {PARTNER}.application WHERE status = 'pending'")
        )
    ).scalar_one()
    by_status = {row[0]: row[1] for row in rows_status}
    by_category = {row[0]: row[1] for row in rows_category}
    return PartnersOverview(
        total=sum(by_status.values()),
        by_status=by_status,
        by_category=by_category,
        pending_applications=int(pending),
    )


async def customers_overview(session: AsyncSession) -> CustomersOverview:
    total = (
        await session.execute(text(f"SELECT COUNT(*) FROM {CORE}.customer"))
    ).scalar_one()
    enrolled = (
        await session.execute(
            text(f"SELECT COUNT(DISTINCT customer_id) FROM {CORE}.enrollment")
        )
    ).scalar_one()
    return CustomersOverview(total=int(total), enrolled=int(enrolled))


async def transactions_overview(
    session: AsyncSession, since: datetime | None = None
) -> TransactionsOverview:
    where = "" if since is None else "WHERE created_at >= :since"
    params: dict[str, object] = {} if since is None else {"since": since}
    sql = text(f"""
        SELECT type, COUNT(*) AS cnt, COALESCE(SUM(points), 0) AS pts
        FROM {CORE}.transaction
        {where}
        GROUP BY type
        """)
    rows = (await session.execute(sql, params)).all()
    aggregates: dict[str, tuple[int, int]] = {
        row[0]: (int(row[1]), int(row[2])) for row in rows
    }
    accruals_count, accruals_points = aggregates.get("accrual", (0, 0))
    redemptions_count, redemptions_points = aggregates.get("redemption", (0, 0))
    reversals_count, _ = aggregates.get("reversal", (0, 0))
    return TransactionsOverview(
        accruals_count=accruals_count,
        accruals_points=accruals_points,
        redemptions_count=redemptions_count,
        redemptions_points=redemptions_points,
        reversals_count=reversals_count,
    )


async def top_partners(
    session: AsyncSession, limit: int = 10, since: datetime | None = None
) -> list[TopPartner]:
    where = "" if since is None else "WHERE t.created_at >= :since"
    params: dict[str, object] = {"limit": limit}
    if since is not None:
        params["since"] = since
    sql = text(f"""
        SELECT
            p.id, p.name,
            COUNT(t.id) AS tx_count,
            COUNT(DISTINCT t.customer_id) AS customers_count
        FROM {CORE}.partner p
        JOIN {CORE}.transaction t ON t.partner_id = p.id
        {where}
        GROUP BY p.id, p.name
        ORDER BY tx_count DESC
        LIMIT :limit
        """)
    rows = (await session.execute(sql, params)).all()
    return [
        TopPartner(
            partner_id=row[0],
            partner_name=row[1],
            transactions_count=int(row[2]),
            customers_count=int(row[3]),
        )
        for row in rows
    ]


async def _daily_counts(
    session: AsyncSession, table: str, days: int
) -> list[DailyCount]:
    since = (datetime.utcnow() - timedelta(days=days - 1)).date()
    sql = text(f"""
        SELECT date_trunc('day', created_at)::date AS day, COUNT(*) AS cnt
        FROM {table}
        WHERE created_at >= :since
        GROUP BY day
        ORDER BY day ASC
        """)
    rows = (await session.execute(sql, {"since": since})).all()
    return [DailyCount(day=row[0], count=int(row[1])) for row in rows]


async def new_customers_by_day(
    session: AsyncSession, days: int = 30
) -> list[DailyCount]:
    return await _daily_counts(session, f"{CORE}.customer", days)


async def new_partners_by_day(
    session: AsyncSession, days: int = 30
) -> list[DailyCount]:
    return await _daily_counts(session, f"{CORE}.partner", days)


async def platform_overview(session: AsyncSession) -> PlatformOverview:
    return PlatformOverview(
        partners=await partners_overview(session),
        customers=await customers_overview(session),
        transactions=await transactions_overview(session),
    )


async def overview_for_period(
    session: AsyncSession, days: int = 30
) -> tuple[date, TransactionsOverview]:
    since_dt = datetime.utcnow() - timedelta(days=days)
    return since_dt.date(), await transactions_overview(session, since=since_dt)
