from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_account_id(
    x_account_id: Annotated[UUID | None, Header(alias="X-Account-Id")] = None,
) -> UUID:
    # TODO: заменить на проверку JWT/сессии партнёра
    if x_account_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Account-Id header is required",
        )
    return x_account_id


async def get_current_admin_id(
    x_admin_id: Annotated[UUID | None, Header(alias="X-Admin-Id")] = None,
) -> UUID:
    # TODO: заменить на проверку токена админа из admin-service
    if x_admin_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Admin-Id header is required",
        )
    return x_admin_id


CurrentAccountId = Annotated[UUID, Depends(get_current_account_id)]
CurrentAdminId = Annotated[UUID, Depends(get_current_admin_id)]
