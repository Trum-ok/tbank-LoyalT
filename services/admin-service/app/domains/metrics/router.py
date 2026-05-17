from fastapi import APIRouter, Query
from loyalt_common import error_responses

from app.deps import CurrentAdmin, SessionDep
from app.domains.metrics import service
from app.domains.metrics.schemas import (
    CustomersOverview,
    DailyCount,
    PartnersOverview,
    PlatformOverview,
    TopPartner,
    TransactionsOverview,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get(
    "/overview",
    response_model=PlatformOverview,
    summary="Сводка по платформе",
    responses=error_responses(401, 403),
)
async def overview(_: CurrentAdmin, session: SessionDep) -> PlatformOverview:
    """Общие агрегаты платформы для дашборда Т-Банка. 401/403 — проблема
    с авторизацией админа."""
    return await service.platform_overview(session)


@router.get(
    "/partners",
    response_model=PartnersOverview,
    summary="Сводка по партнёрам",
    responses=error_responses(401, 403),
)
async def partners(_: CurrentAdmin, session: SessionDep) -> PartnersOverview:
    """Агрегаты по партнёрам (всего, по статусам). 401/403 — проблема с
    авторизацией админа."""
    return await service.partners_overview(session)


@router.get(
    "/customers",
    response_model=CustomersOverview,
    summary="Сводка по клиентам",
    responses=error_responses(401, 403),
)
async def customers(_: CurrentAdmin, session: SessionDep) -> CustomersOverview:
    """Агрегаты по клиентам платформы. 401/403 — проблема с авторизацией
    админа."""
    return await service.customers_overview(session)


@router.get(
    "/transactions",
    response_model=TransactionsOverview,
    summary="Сводка по транзакциям",
    responses=error_responses(401, 403),
)
async def transactions(
    _: CurrentAdmin,
    session: SessionDep,
    days: int | None = Query(default=None, ge=1, le=365),
) -> TransactionsOverview:
    """Агрегаты по операциям с баллами; `days` ограничивает период
    последними N днями. 401/403 — проблема с авторизацией админа."""
    if days is None:
        return await service.transactions_overview(session)
    _since, result = await service.overview_for_period(session, days=days)
    return result


@router.get(
    "/top-partners",
    response_model=list[TopPartner],
    summary="Топ партнёров",
    responses=error_responses(401, 403),
)
async def top_partners(
    _: CurrentAdmin,
    session: SessionDep,
    limit: int = Query(default=10, ge=1, le=50),
    days: int | None = Query(default=None, ge=1, le=365),
) -> list[TopPartner]:
    """Партнёры с наибольшей активностью; `days` ограничивает период.
    401/403 — проблема с авторизацией админа."""
    since = None
    if days is not None:
        from datetime import datetime, timedelta

        since = datetime.utcnow() - timedelta(days=days)
    return await service.top_partners(session, limit=limit, since=since)


@router.get(
    "/new-customers",
    response_model=list[DailyCount],
    summary="Новые клиенты по дням",
    responses=error_responses(401, 403),
)
async def new_customers(
    _: CurrentAdmin,
    session: SessionDep,
    days: int = Query(default=30, ge=1, le=365),
) -> list[DailyCount]:
    """Количество новых клиентов по дням за последние `days` дней.
    401/403 — проблема с авторизацией админа."""
    return await service.new_customers_by_day(session, days=days)


@router.get(
    "/new-partners",
    response_model=list[DailyCount],
    summary="Новые партнёры по дням",
    responses=error_responses(401, 403),
)
async def new_partners(
    _: CurrentAdmin,
    session: SessionDep,
    days: int = Query(default=30, ge=1, le=365),
) -> list[DailyCount]:
    """Количество новых партнёров по дням за последние `days` дней.
    401/403 — проблема с авторизацией админа."""
    return await service.new_partners_by_day(session, days=days)
