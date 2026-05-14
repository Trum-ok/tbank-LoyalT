from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentAdmin, SessionDep
from app.domains.admins import service
from app.domains.admins.models import AdminAccount
from app.domains.admins.schemas import AdminCreate, AdminRead, AdminUpdate

router = APIRouter(prefix="/admins", tags=["admins"])


async def _require_admin_or_bootstrap(
    session: AsyncSession, x_admin_id: UUID | None
) -> None:
    """Создавать админа можно либо когда таблица пуста (bootstrap),
    либо если запрос делает уже существующий активный админ."""
    count = await service.count_admins(session)
    if count == 0:
        return
    if x_admin_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Admin-Id header is required",
        )
    admin = await session.get(AdminAccount, x_admin_id)
    if admin is None or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an active admin can create new admins",
        )


@router.post("", response_model=AdminRead, status_code=status.HTTP_201_CREATED)
async def create_admin(
    data: AdminCreate,
    session: SessionDep,
    x_admin_id: UUID | None = Header(default=None, alias="X-Admin-Id"),
) -> AdminRead:
    await _require_admin_or_bootstrap(session, x_admin_id)
    admin = await service.create_admin(session, data)
    return AdminRead.model_validate(admin)


@router.get("", response_model=list[AdminRead])
async def list_admins(_: CurrentAdmin, session: SessionDep) -> list[AdminRead]:
    admins = await service.list_admins(session)
    return [AdminRead.model_validate(a) for a in admins]


@router.get("/me", response_model=AdminRead)
async def me(admin: CurrentAdmin) -> AdminRead:
    return AdminRead.model_validate(admin)


@router.patch("/{admin_id}", response_model=AdminRead)
async def update_admin(
    admin_id: UUID,
    data: AdminUpdate,
    _: CurrentAdmin,
    session: SessionDep,
) -> AdminRead:
    admin = await service.update_admin(session, admin_id, data)
    return AdminRead.model_validate(admin)
