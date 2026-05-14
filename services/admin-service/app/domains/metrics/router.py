from fastapi import APIRouter, Query

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


@router.get("/overview", response_model=PlatformOverview)
async def overview(_: CurrentAdmin, session: SessionDep) -> PlatformOverview:
    return await service.platform_overview(session)


@router.get("/partners", response_model=PartnersOverview)
async def partners(_: CurrentAdmin, session: SessionDep) -> PartnersOverview:
    return await service.partners_overview(session)


@router.get("/customers", response_model=CustomersOverview)
async def customers(_: CurrentAdmin, session: SessionDep) -> CustomersOverview:
    return await service.customers_overview(session)


@router.get("/transactions", response_model=TransactionsOverview)
async def transactions(
    _: CurrentAdmin,
    session: SessionDep,
    days: int | None = Query(default=None, ge=1, le=365),
) -> TransactionsOverview:
    if days is None:
        return await service.transactions_overview(session)
    _, result = await service.overview_for_period(session, days=days)
    return result


@router.get("/top-partners", response_model=list[TopPartner])
async def top_partners(
    _: CurrentAdmin,
    session: SessionDep,
    limit: int = Query(default=10, ge=1, le=50),
    days: int | None = Query(default=None, ge=1, le=365),
) -> list[TopPartner]:
    since = None
    if days is not None:
        from datetime import datetime, timedelta

        since = datetime.utcnow() - timedelta(days=days)
    return await service.top_partners(session, limit=limit, since=since)


@router.get("/new-customers", response_model=list[DailyCount])
async def new_customers(
    _: CurrentAdmin,
    session: SessionDep,
    days: int = Query(default=30, ge=1, le=365),
) -> list[DailyCount]:
    return await service.new_customers_by_day(session, days=days)


@router.get("/new-partners", response_model=list[DailyCount])
async def new_partners(
    _: CurrentAdmin,
    session: SessionDep,
    days: int = Query(default=30, ge=1, le=365),
) -> list[DailyCount]:
    return await service.new_partners_by_day(session, days=days)
