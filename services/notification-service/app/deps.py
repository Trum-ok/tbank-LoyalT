from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_customer_id(
    x_customer_id: Annotated[UUID | None, Header(alias="X-Customer-Id")] = None,
) -> UUID:
    # TODO: заменить на T-ID, как только подключим реальный auth
    if x_customer_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Customer-Id header is required",
        )
    return x_customer_id


CurrentCustomerId = Annotated[UUID, Depends(get_current_customer_id)]
