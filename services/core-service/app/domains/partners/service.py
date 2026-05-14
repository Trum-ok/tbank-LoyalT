from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.partners.models import Partner
from app.domains.partners.schemas import PartnerCreate, PartnerUpdate
from app.errors import ConflictError, NotFoundError


async def create_partner(session: AsyncSession, data: PartnerCreate) -> Partner:
    partner = Partner(**data.model_dump())
    session.add(partner)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Partner with this INN already exists") from exc
    await session.refresh(partner)
    return partner


async def get_partner(session: AsyncSession, partner_id: UUID) -> Partner:
    partner = await session.get(Partner, partner_id)
    if partner is None:
        raise NotFoundError("Partner not found")
    return partner


async def list_partners(session: AsyncSession) -> list[Partner]:
    result = await session.execute(select(Partner).order_by(Partner.created_at.desc()))
    return list(result.scalars().all())


async def update_partner(
    session: AsyncSession, partner_id: UUID, data: PartnerUpdate
) -> Partner:
    partner = await get_partner(session, partner_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(partner, field, value)
    await session.commit()
    await session.refresh(partner)
    return partner
