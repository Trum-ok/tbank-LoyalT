from uuid import UUID

from fastapi import APIRouter, status

from app.deps import SessionDep
from app.domains.partners import service
from app.domains.partners.schemas import PartnerCreate, PartnerRead, PartnerUpdate

router = APIRouter(prefix="/partners", tags=["partners"])


@router.post("", response_model=PartnerRead, status_code=status.HTTP_201_CREATED)
async def create_partner(data: PartnerCreate, session: SessionDep) -> PartnerRead:
    partner = await service.create_partner(session, data)
    return PartnerRead.model_validate(partner)


@router.get("", response_model=list[PartnerRead])
async def list_partners(session: SessionDep) -> list[PartnerRead]:
    partners = await service.list_partners(session)
    return [PartnerRead.model_validate(p) for p in partners]


@router.get("/{partner_id}", response_model=PartnerRead)
async def get_partner(partner_id: UUID, session: SessionDep) -> PartnerRead:
    partner = await service.get_partner(session, partner_id)
    return PartnerRead.model_validate(partner)


@router.patch("/{partner_id}", response_model=PartnerRead)
async def update_partner(
    partner_id: UUID, data: PartnerUpdate, session: SessionDep
) -> PartnerRead:
    partner = await service.update_partner(session, partner_id, data)
    return PartnerRead.model_validate(partner)
