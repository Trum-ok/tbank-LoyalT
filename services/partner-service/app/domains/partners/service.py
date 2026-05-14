from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.applications.service import approve as approve_application
from app.domains.partners.models import Partner, PartnerStatus
from app.domains.partners.schemas import PartnerUpdate
from app.errors import ConflictError, NotFoundError
from app.events import publisher


def _to_event_payload(partner: Partner) -> dict:
    return {
        "partner_id": partner.id,
        "account_id": partner.account_id,
        "application_id": partner.application_id,
        "name": partner.name,
        "inn": partner.inn,
        "category": partner.category,
        "logo_url": partner.logo_url,
        "brand_color": partner.brand_color,
        "status": partner.status,
        "contact_email": partner.contact_email,
        "contact_phone": partner.contact_phone,
    }


async def approve_application_and_create_partner(
    session: AsyncSession,
    application_id: UUID,
    admin_id: UUID,
    comment: str | None = None,
) -> Partner:
    """Одобрить заявку и создать партнёра в одной транзакции, опубликовать событие."""
    application = await approve_application(session, application_id, admin_id, comment)

    partner = Partner(
        account_id=application.account_id,
        application_id=application.id,
        name=application.business_name,
        inn=application.inn,
        category=application.category,
        contact_email=application.contact_email,
        contact_phone=application.contact_phone,
    )
    session.add(partner)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "Partner with this INN or account already exists"
        ) from exc
    await session.refresh(partner)

    await publisher.publish(
        "partner.approved",
        _to_event_payload(partner),
        key=str(partner.id),
    )
    return partner


async def get_partner(session: AsyncSession, partner_id: UUID) -> Partner:
    partner = await session.get(Partner, partner_id)
    if partner is None:
        raise NotFoundError("Partner not found")
    return partner


async def get_partner_by_account(session: AsyncSession, account_id: UUID) -> Partner:
    result = await session.execute(select(Partner).where(Partner.account_id == account_id))
    partner = result.scalar_one_or_none()
    if partner is None:
        raise NotFoundError("Partner not found for this account")
    return partner


async def list_partners(
    session: AsyncSession,
    status_filter: PartnerStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Partner]:
    stmt = select(Partner)
    if status_filter is not None:
        stmt = stmt.where(Partner.status == status_filter)
    stmt = stmt.order_by(Partner.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_partner_profile(
    session: AsyncSession, account_id: UUID, data: PartnerUpdate
) -> Partner:
    partner = await get_partner_by_account(session, account_id)
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        return partner
    for field, value in changes.items():
        setattr(partner, field, value)
    await session.commit()
    await session.refresh(partner)
    await publisher.publish(
        "partner.updated", _to_event_payload(partner), key=str(partner.id)
    )
    return partner


async def set_status(
    session: AsyncSession, partner_id: UUID, target: PartnerStatus
) -> Partner:
    partner = await get_partner(session, partner_id)
    if partner.status == target:
        return partner
    partner.status = target
    await session.commit()
    await session.refresh(partner)
    await publisher.publish(
        "partner.status_changed",
        _to_event_payload(partner),
        key=str(partner.id),
    )
    return partner


