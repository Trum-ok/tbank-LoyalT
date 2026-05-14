from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.admins.models import AdminAccount
from app.domains.admins.schemas import AdminCreate, AdminUpdate
from app.errors import ConflictError, NotFoundError


async def count_admins(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(AdminAccount.id)))
    return int(result.scalar_one())


async def create_admin(session: AsyncSession, data: AdminCreate) -> AdminAccount:
    admin = AdminAccount(email=str(data.email).lower(), full_name=data.full_name)
    session.add(admin)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Admin with this email already exists") from exc
    await session.refresh(admin)
    return admin


async def get_admin(session: AsyncSession, admin_id: UUID) -> AdminAccount:
    admin = await session.get(AdminAccount, admin_id)
    if admin is None:
        raise NotFoundError("Admin not found")
    return admin


async def list_admins(session: AsyncSession) -> list[AdminAccount]:
    result = await session.execute(
        select(AdminAccount).order_by(AdminAccount.created_at.desc())
    )
    return list(result.scalars().all())


async def update_admin(
    session: AsyncSession, admin_id: UUID, data: AdminUpdate
) -> AdminAccount:
    admin = await get_admin(session, admin_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(admin, field, value)
    await session.commit()
    await session.refresh(admin)
    return admin
