from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_customer_id(
    x_customer_id: Annotated[UUID | None, Header(alias="X-Customer-Id")] = None,
) -> UUID:
    # TODO: заменить на проверку T-ID через API Gateway / JWT
    if x_customer_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Customer-Id header is required",
        )
    return x_customer_id


async def get_current_partner_id(
    x_partner_id: Annotated[UUID | None, Header(alias="X-Partner-Id")] = None,
) -> UUID:
    # TODO: заменить на проверку токена партнёра из partner-service
    if x_partner_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Partner-Id header is required",
        )
    return x_partner_id


CurrentCustomerId = Annotated[UUID, Depends(get_current_customer_id)]
CurrentPartnerId = Annotated[UUID, Depends(get_current_partner_id)]
