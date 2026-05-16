from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.partners.models import Partner
from app.domains.staff.models import Staff
from app.domains.staff.schemas import StaffCreate, StaffUpdate
from app.domains.staff.security import hash_pin, verify_pin
from app.errors import ConflictError, ForbiddenError, NotFoundError


async def create_staff(
    session: AsyncSession, partner_id: UUID, data: StaffCreate
) -> Staff:
    staff = Staff(
        partner_id=partner_id,
        name=data.name,
        login_code=data.login_code,
        pin_hash=hash_pin(data.pin),
    )
    session.add(staff)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Staff login_code is already taken") from exc
    await session.refresh(staff)
    return staff


async def list_staff(session: AsyncSession, partner_id: UUID) -> list[Staff]:
    stmt = (
        select(Staff)
        .where(Staff.partner_id == partner_id)
        .order_by(Staff.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _get_owned(session: AsyncSession, staff_id: UUID, partner_id: UUID) -> Staff:
    staff = await session.get(Staff, staff_id)
    if staff is None:
        raise NotFoundError("Staff not found")
    if staff.partner_id != partner_id:
        raise ForbiddenError("Staff belongs to another partner")
    return staff


async def update_staff(
    session: AsyncSession, staff_id: UUID, partner_id: UUID, data: StaffUpdate
) -> Staff:
    staff = await _get_owned(session, staff_id, partner_id)
    changes = data.model_dump(exclude_unset=True)
    if "pin" in changes:
        staff.pin_hash = hash_pin(changes.pop("pin"))
    for field, value in changes.items():
        setattr(staff, field, value)
    await session.commit()
    await session.refresh(staff)
    return staff


async def delete_staff(session: AsyncSession, staff_id: UUID, partner_id: UUID) -> None:
    staff = await _get_owned(session, staff_id, partner_id)
    await session.delete(staff)
    await session.commit()


async def get_staff(session: AsyncSession, staff_id: UUID) -> Staff:
    staff = await session.get(Staff, staff_id)
    if staff is None:
        raise NotFoundError("Staff not found")
    return staff


async def authenticate(
    session: AsyncSession, login_code: str, pin: str
) -> tuple[Staff, Partner]:
    result = await session.execute(select(Staff).where(Staff.login_code == login_code))
    staff = result.scalar_one_or_none()
    if staff is None or not staff.is_active or not verify_pin(pin, staff.pin_hash):
        raise ForbiddenError("Invalid login code or PIN")
    partner = await session.get(Partner, staff.partner_id)
    if partner is None:
        raise NotFoundError("Partner not found for this staff")
    return staff, partner
