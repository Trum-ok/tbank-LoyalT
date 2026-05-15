from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.jwt_tokens import TokenError, decode

settings = get_settings()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _partner_id_from_bearer(authorization: str | None) -> UUID | None:
    """Достаёт partner_id из токена кассира. None — если Bearer нет."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization[7:].strip()
    try:
        payload = decode(token, secret=settings.jwt_secret)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if payload.get("typ") != "staff" or "pid" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a valid staff token",
        )
    return UUID(str(payload["pid"]))


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
    authorization: Annotated[str | None, Header()] = None,
    x_partner_id: Annotated[UUID | None, Header(alias="X-Partner-Id")] = None,
) -> UUID:
    """Касса: Bearer-JWT кассира (partner_id берётся из токена).

    Fallback на X-Partner-Id — это легаси-стаб ЛК партнёра, пока там нет
    собственного JWT (TODO: заменить на токен партнёра из partner-service).
    """
    partner_id = _partner_id_from_bearer(authorization)
    if partner_id is not None:
        return partner_id
    if x_partner_id is not None:
        return x_partner_id
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authorization (Bearer) or X-Partner-Id is required",
    )


CurrentCustomerId = Annotated[UUID, Depends(get_current_customer_id)]
CurrentPartnerId = Annotated[UUID, Depends(get_current_partner_id)]
