from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.domains.admins.models import AdminAccount

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_admin(
    session: SessionDep,
    x_admin_id: Annotated[UUID | None, Header(alias="X-Admin-Id")] = None,
) -> AdminAccount:
    # TODO: заменить заголовок на JWT, когда подключим auth для админов
    if x_admin_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Admin-Id header is required",
        )
    admin = await session.get(AdminAccount, x_admin_id)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown admin"
        )
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin is inactive"
        )
    return admin


CurrentAdmin = Annotated[AdminAccount, Depends(get_current_admin)]
