from uuid import UUID

from fastapi import APIRouter, Query

from app.deps import CurrentAccountId, CurrentAdminId, SessionDep
from app.domains.partners import service
from app.domains.partners.models import PartnerStatus
from app.domains.partners.schemas import PartnerRead, PartnerUpdate

partner_router = APIRouter(prefix="/partners", tags=["partners"])
admin_router = APIRouter(prefix="/admin/partners", tags=["partners-admin"])


@partner_router.get("/me", response_model=PartnerRead)
async def get_my_partner(
    account_id: CurrentAccountId, session: SessionDep
) -> PartnerRead:
    partner = await service.get_partner_by_account(session, account_id)
    return PartnerRead.model_validate(partner)


@partner_router.patch("/me", response_model=PartnerRead)
async def update_my_partner(
    data: PartnerUpdate,
    account_id: CurrentAccountId,
    session: SessionDep,
) -> PartnerRead:
    partner = await service.update_partner_profile(session, account_id, data)
    return PartnerRead.model_validate(partner)


@admin_router.get("", response_model=list[PartnerRead])
async def list_partners(
    session: SessionDep,
    _admin: CurrentAdminId,
    status_filter: PartnerStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PartnerRead]:
    partners = await service.list_partners(
        session, status_filter=status_filter, limit=limit, offset=offset
    )
    return [PartnerRead.model_validate(p) for p in partners]


@admin_router.get("/{partner_id}", response_model=PartnerRead)
async def get_partner(
    partner_id: UUID, session: SessionDep, _admin: CurrentAdminId
) -> PartnerRead:
    partner = await service.get_partner(session, partner_id)
    return PartnerRead.model_validate(partner)


@admin_router.post("/{partner_id}/suspend", response_model=PartnerRead)
async def suspend_partner(
    partner_id: UUID, session: SessionDep, _admin: CurrentAdminId
) -> PartnerRead:
    partner = await service.set_status(session, partner_id, PartnerStatus.SUSPENDED)
    return PartnerRead.model_validate(partner)


@admin_router.post("/{partner_id}/block", response_model=PartnerRead)
async def block_partner(
    partner_id: UUID, session: SessionDep, _admin: CurrentAdminId
) -> PartnerRead:
    partner = await service.set_status(session, partner_id, PartnerStatus.BLOCKED)
    return PartnerRead.model_validate(partner)


@admin_router.post("/{partner_id}/unblock", response_model=PartnerRead)
async def unblock_partner(
    partner_id: UUID, session: SessionDep, _admin: CurrentAdminId
) -> PartnerRead:
    partner = await service.set_status(session, partner_id, PartnerStatus.ACTIVE)
    return PartnerRead.model_validate(partner)
