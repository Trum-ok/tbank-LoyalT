from enum import StrEnum

from pydantic import BaseModel


class Period(StrEnum):
    """Окно дашборда. ALL — за всё время с первой активности партнёра."""

    D1 = "1d"
    D7 = "7d"
    D14 = "14d"
    D30 = "30d"
    D90 = "90d"
    ALL = "all"


class DayCount(BaseModel):
    date: str  # YYYY-MM-DD
    count: int


class PurchasesPerUserDay(BaseModel):
    date: str  # YYYY-MM-DD
    purchases: int
    users: int
    ratio: float  # purchases / users


class Summary(BaseModel):
    active_customers: int
    accrued: int
    redeemed: int
    average_check: float


class Stickiness(BaseModel):
    # Средние посуточные активные / активные за окно.
    dau: float  # среднесуточные активные клиенты за период
    wau: int  # уникальные активные за последние 7 дней
    mau: int  # уникальные активные за последние 30 дней
    dau_wau_pct: float
    dau_mau_pct: float


class RetentionPoint(BaseModel):
    day: int  # смещение от дня первого вступления
    retention: float  # доля когорты, активная в этот день (0..1)


class Retention(BaseModel):
    cohort_size: int
    d1: float | None
    d7: float | None
    d30: float | None
    curve: list[RetentionPoint]
    # День, к которому удержание впервые падает <= 50% (медианный отток).
    median_churn_day: int | None


class HeatCell(BaseModel):
    dow: int  # 0 = понедельник ... 6 = воскресенье
    hour: int  # 0..23
    count: int


class Heatmap(BaseModel):
    max: int
    cells: list[HeatCell]


class AnalyticsRead(BaseModel):
    period: Period
    summary: Summary
    new_users_by_day: list[DayCount]
    purchases_per_user_by_day: list[PurchasesPerUserDay]
    stickiness: Stickiness
    retention: Retention
    heatmap: Heatmap
