from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.domains.staff import tokens
from app.jwt_tokens import TokenError

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization[7:].strip()


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


async def get_current_partner_id(
    x_partner_id: Annotated[UUID | None, Header(alias="X-Partner-Id")] = None,
) -> UUID:
    """Партнёр-скоуп ЛК: id берётся из X-Partner-Id.

    Совпадает с моделью core-service (тот же стаб-заголовок). Не выводим
    партнёра из X-Account-Id, т.к. account_id создаётся при онбординге и
    в дев-личностях может не совпадать, а partner_id стабилен.
    TODO: заменить на JWT партнёра.
    """
    if x_partner_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Partner-Id header is required",
        )
    return x_partner_id


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


async def get_current_staff_id(
    authorization: Annotated[str | None, Header()] = None,
) -> UUID:
    """Кассир: Bearer-JWT, выданный на /staff/login."""
    token = _bearer(authorization)
    try:
        staff_id, _partner_id = tokens.parse(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return staff_id


CurrentAccountId = Annotated[UUID, Depends(get_current_account_id)]
CurrentPartnerId = Annotated[UUID, Depends(get_current_partner_id)]
CurrentAdminId = Annotated[UUID, Depends(get_current_admin_id)]
CurrentStaffId = Annotated[UUID, Depends(get_current_staff_id)]
