"""Серверная агрегация метрик дашборда партнёра.

Все тяжёлые расчёты делаются здесь (а не на фронте), чтобы не упираться
в limit транзакций и не тянуть «сырьё» в браузер. Данные забираются двумя
минимальными запросами и сворачиваются в Python — для масштабов хакатона
этого достаточно, при росте легко заменить на SQL group by.

Время в created_at наивное (func.now() в БД). Трактуем как UTC и бакетим
по календарной дате/часу UTC.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.domains.transactions.models import Transaction, TransactionType

_PERIOD_DAYS: dict[Period, int | None] = {
    Period.D1: 1,
    Period.D7: 7,
    Period.D14: 14,
    Period.D30: 30,
    Period.D90: 90,
    Period.ALL: None,
}

# Кривую удержания строим максимум на столько дней — дальше шум по краям когорт.
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
    window_start_dt = None if days is None else now - timedelta(days=days)

    # 1. Вступления партнёра (за всё время — нужно для «новых юзеров» и когорт).
    enroll_rows = (
        await session.execute(
            select(Enrollment.customer_id, Enrollment.created_at)
            .join(Program, Program.id == Enrollment.program_id)
            .where(Program.partner_id == partner_id)
        )
    ).all()

    # 2. Транзакции партнёра за всё время — для retention по краевым когортам.
    tx_rows = (
        await session.execute(
            select(
                Transaction.customer_id,
                Transaction.type,
                Transaction.purchase_amount,
                Transaction.points,
                Transaction.is_reversed,
                Transaction.created_at,
            ).where(Transaction.partner_id == partner_id)
        )
    ).all()

    # --- День первого вступления на клиента (= «новый юзер» для партнёра) ---
    first_enroll: dict[UUID, date] = {}
    for cust, created in enroll_rows:
        d = created.date()
        if cust not in first_enroll or d < first_enroll[cust]:
            first_enroll[cust] = d

    # Активность по дням на клиента (любая нереверсная операция = вовлечённость).
    activity_days: dict[UUID, set[date]] = defaultdict(set)
    for cust, ttype, _amount, _pts, _rev, created in tx_rows:
        if ttype == TransactionType.REVERSAL:
            continue
        activity_days[cust].add(created.date())

    # ---------------- Окно периода ----------------
    if window_start_dt is None:
        candidate_dates = [d for d in first_enroll.values()]
        candidate_dates += [r[5].date() for r in tx_rows]
        start_date = min(candidate_dates) if candidate_dates else today
    else:
        start_date = window_start_dt.date()
    window_days = _day_range(start_date, today)

    in_window = (
        lambda dt: window_start_dt is None or dt >= window_start_dt
    )

    # ---------------- Новые юзеры по дням ----------------
    new_by_day: dict[date, int] = {d: 0 for d in window_days}
    for d in first_enroll.values():
        if start_date <= d <= today:
            new_by_day[d] = new_by_day.get(d, 0) + 1
    new_users_by_day = [
        DayCount(date=d.isoformat(), count=new_by_day[d]) for d in window_days
    ]

    # ---------------- Покупки / юзер по дням + summary ----------------
    purchases_day: dict[date, int] = {d: 0 for d in window_days}
    users_day: dict[date, set[UUID]] = {d: set() for d in window_days}
    accrued = 0
    redeemed = 0
    check_sum = Decimal(0)
    check_n = 0
    active_customers: set[UUID] = set()

    for cust, ttype, amount, pts, rev, created in tx_rows:
        if not in_window(created):
            continue
        if ttype == TransactionType.REVERSAL:
            continue
        d = created.date()
        active_customers.add(cust)
        if d in users_day:
            users_day[d].add(cust)
        if ttype == TransactionType.ACCRUAL:
            if d in purchases_day:
                purchases_day[d] += 1
            if not rev:
                accrued += pts
            if amount is not None:
                check_sum += amount
                check_n += 1
        elif ttype == TransactionType.REDEMPTION:
            redeemed += pts

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
    daily_active: dict[date, set[UUID]] = defaultdict(set)
    for cust, ttype, _a, _p, _r, created in tx_rows:
        if ttype == TransactionType.REVERSAL:
            continue
        if not in_window(created):
            continue
        daily_active[created.date()].add(cust)

    n_days = max(len(window_days), 1)
    dau = sum(len(s) for s in daily_active.values()) / n_days

    wau_set: set[UUID] = set()
    mau_set: set[UUID] = set()
    w7 = now - timedelta(days=7)
    w30 = now - timedelta(days=30)
    for cust, ttype, _a, _p, _r, created in tx_rows:
        if ttype == TransactionType.REVERSAL:
            continue
        if created >= w7:
            wau_set.add(cust)
        if created >= w30:
            mau_set.add(cust)
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
    # Когорта = клиенты, чьё первое вступление попало в окно периода.
    # Удержание Dn = доля когорты, у кого была активность ровно в день +n
    # (учитываем только тех, у кого день +n уже физически наступил).
    cohort = [
        c
        for c, d in first_enroll.items()
        if start_date <= d <= today
    ]
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
                    continue  # день +offset ещё не наступил
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
    for _cust, ttype, _a, _p, _r, created in tx_rows:
        if ttype == TransactionType.REVERSAL:
            continue
        if not in_window(created):
            continue
        grid[(created.weekday(), created.hour)] += 1
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
