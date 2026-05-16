from fastapi import APIRouter, Query

from app.deps import CurrentPartnerId, SessionDep
from app.domains.analytics import service
from app.domains.analytics.schemas import AnalyticsRead, Period

partner_router = APIRouter(prefix="/partner/analytics", tags=["analytics"])


@partner_router.get("", response_model=AnalyticsRead)
async def get_partner_analytics(
    partner_id: CurrentPartnerId,
    session: SessionDep,
    period: Period = Query(default=Period.D30),
) -> AnalyticsRead:
    return await service.build_partner_analytics(session, partner_id, period)
