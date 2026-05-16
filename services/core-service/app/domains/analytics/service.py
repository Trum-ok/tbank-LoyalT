"""Серверная агрегация метрик дашборда партнёра.

Тяжёлые метрики считаются из read-модели (analytics_daily / analytics_heatmap,
см. domains.analytics.projection), а не сканом transaction. Лёгкий запрос
вступлений остаётся (enrollments на порядки меньше транзакций) — он нужен
для «новых юзеров» и когорт retention.

Семантика повторяет прежнюю реализацию (наличие дневной строки = клиент
активен; reversal исключён; reversed accrual теряет баллы, но активность
и чек остаются). Окно периода фильтруется по календарной дате UTC —
небольшое отличие от прежней фильтрации по timestamp осознанное.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analytics.projection import AnalyticsDaily, AnalyticsHeatmap
from app.domains.analytics.schemas import (
    AnalyticsRead,
    DayCount,
    HeatCell,
    Heatmap,
    Period,
    PurchasesPerUserDay,
    Retention,
    RetentionPoint,
    Stickiness,
    Summary,
)
from app.domains.enrollments.models import Enrollment
from app.domains.programs.models import Program

_PERIOD_DAYS: dict[Period, int | None] = {
    Period.D1: 1,
    Period.D7: 7,
    Period.D14: 14,
    Period.D30: 30,
    Period.D90: 90,
    Period.ALL: None,
}

_MAX_RETENTION_DAY = 90


def _day_range(start: date, end: date) -> list[date]:
    out: list[date] = []
    cur = start
    while cur <= end:
        out.append(cur)
        cur += timedelta(days=1)
    return out


async def build_partner_analytics(
    session: AsyncSession, partner_id: UUID, period: Period
) -> AnalyticsRead:
    now = datetime.utcnow()
    today = now.date()
    days = _PERIOD_DAYS[period]
    window_start = None if days is None else (now - timedelta(days=days)).date()

    # 1. Вступления партнёра (за всё время) — для «новых юзеров» и когорт.
    enroll_rows = (
        await session.execute(
            select(Enrollment.customer_id, Enrollment.created_at)
            .join(Program, Program.id == Enrollment.program_id)
            .where(Program.partner_id == partner_id)
        )
    ).all()

    # 2. Дневная проекция партнёра (за всё время — нужно для retention).
    daily_rows = (
        await session.execute(
            select(
                AnalyticsDaily.customer_id,
                AnalyticsDaily.day,
                AnalyticsDaily.accrual_count,
                AnalyticsDaily.accrued_points,
                AnalyticsDaily.redeemed_points,
                AnalyticsDaily.purchase_amount_sum,
                AnalyticsDaily.purchase_count,
            ).where(AnalyticsDaily.partner_id == partner_id)
        )
    ).all()

    # 3. Heatmap-проекция партнёра.
    heat_rows = (
        await session.execute(
            select(
                AnalyticsHeatmap.day,
                AnalyticsHeatmap.hour,
                AnalyticsHeatmap.cnt,
            ).where(AnalyticsHeatmap.partner_id == partner_id)
        )
    ).all()

    # День первого вступления на клиента (= «новый юзер» для партнёра).
    first_enroll: dict[UUID, date] = {}
    for cust, created in enroll_rows:
        d = created.date()
        if cust not in first_enroll or d < first_enroll[cust]:
            first_enroll[cust] = d

    # Дни активности на клиента (все строки проекции = нереверсная активность).
    activity_days: dict[UUID, set[date]] = defaultdict(set)
    for cust, d, *_rest in daily_rows:
        activity_days[cust].add(d)

    # ---------------- Окно периода ----------------
    if window_start is None:
        candidates: list[date] = list(first_enroll.values())
        candidates += [r[1] for r in daily_rows]
        candidates += [r[0] for r in heat_rows]
        start_date = min(candidates) if candidates else today
    else:
        start_date = window_start
    window_days = _day_range(start_date, today)

    def in_window(d: date) -> bool:
        return window_start is None or d >= window_start

    # ---------------- Новые юзеры по дням ----------------
    new_by_day: dict[date, int] = {d: 0 for d in window_days}
    for d in first_enroll.values():
        if start_date <= d <= today:
            new_by_day[d] = new_by_day.get(d, 0) + 1
    new_users_by_day = [
        DayCount(date=d.isoformat(), count=new_by_day[d]) for d in window_days
    ]

    # ---------------- Summary + покупки/юзер по дням ----------------
    purchases_day: dict[date, int] = {d: 0 for d in window_days}
    users_day: dict[date, set[UUID]] = {d: set() for d in window_days}
    accrued = 0
    redeemed = 0
    check_sum = Decimal(0)
    check_n = 0
    active_customers: set[UUID] = set()
    daily_active: dict[date, set[UUID]] = defaultdict(set)
    wau_set: set[UUID] = set()
    mau_set: set[UUID] = set()
    w7 = (now - timedelta(days=7)).date()
    w30 = (now - timedelta(days=30)).date()

    for (
        cust,
        d,
        accrual_count,
        accrued_points,
        redeemed_points,
        purchase_sum,
        purchase_count,
    ) in daily_rows:
        if not in_window(d):
            continue
        active_customers.add(cust)
        daily_active[d].add(cust)
        if d >= w7:
            wau_set.add(cust)
        if d >= w30:
            mau_set.add(cust)
        if d in users_day:
            users_day[d].add(cust)
            purchases_day[d] += accrual_count
        accrued += accrued_points
        redeemed += redeemed_points
        check_sum += purchase_sum
        check_n += purchase_count

    purchases_per_user_by_day = []
    for d in window_days:
        u = len(users_day[d])
        p = purchases_day[d]
        purchases_per_user_by_day.append(
            PurchasesPerUserDay(
                date=d.isoformat(),
                purchases=p,
                users=u,
                ratio=round(p / u, 2) if u else 0.0,
            )
        )

    summary = Summary(
        active_customers=len(active_customers),
        accrued=accrued,
        redeemed=redeemed,
        average_check=round(float(check_sum) / check_n, 2) if check_n else 0.0,
    )

    # ---------------- Stickiness: DAU / WAU / MAU ----------------
    n_days = max(len(window_days), 1)
    dau = sum(len(s) for s in daily_active.values()) / n_days
    wau = len(wau_set)
    mau = len(mau_set)
    stickiness = Stickiness(
        dau=round(dau, 1),
        wau=wau,
        mau=mau,
        dau_wau_pct=round(dau / wau * 100, 1) if wau else 0.0,
        dau_mau_pct=round(dau / mau * 100, 1) if mau else 0.0,
    )

    # ---------------- Retention ----------------
    cohort = [c for c, d in first_enroll.items() if start_date <= d <= today]
    cohort_size = len(cohort)
    curve: list[RetentionPoint] = []
    d1 = d7 = d30 = None
    median_churn_day: int | None = None

    if cohort_size:
        max_day = min(
            _MAX_RETENTION_DAY,
            max((today - first_enroll[c]).days for c in cohort),
        )
        for offset in range(0, max_day + 1):
            eligible = 0
            retained = 0
            for c in cohort:
                base = first_enroll[c]
                if (today - base).days < offset:
                    continue
                eligible += 1
                if (base + timedelta(days=offset)) in activity_days.get(c, ()):
                    retained += 1
            ret = retained / eligible if eligible else 0.0
            curve.append(RetentionPoint(day=offset, retention=round(ret, 4)))
            if offset == 1:
                d1 = round(ret, 4) if eligible else None
            elif offset == 7:
                d7 = round(ret, 4) if eligible else None
            elif offset == 30:
                d30 = round(ret, 4) if eligible else None
            if (
                median_churn_day is None
                and offset >= 1
                and eligible
                and ret <= 0.5
            ):
                median_churn_day = offset

    retention = Retention(
        cohort_size=cohort_size,
        d1=d1,
        d7=d7,
        d30=d30,
        curve=curve,
        median_churn_day=median_churn_day,
    )

    # ---------------- Heatmap: день недели × час ----------------
    grid: dict[tuple[int, int], int] = defaultdict(int)
    for d, hour, cnt in heat_rows:
        if not in_window(d):
            continue
        grid[(d.weekday(), hour)] += cnt
    cells = [
        HeatCell(dow=dow, hour=hour, count=grid.get((dow, hour), 0))
        for dow in range(7)
        for hour in range(24)
    ]
    heatmap = Heatmap(
        max=max(grid.values()) if grid else 0,
        cells=cells,
    )

    return AnalyticsRead(
        period=period,
        summary=summary,
        new_users_by_day=new_users_by_day,
        purchases_per_user_by_day=purchases_per_user_by_day,
        stickiness=stickiness,
        retention=retention,
        heatmap=heatmap,
    )
