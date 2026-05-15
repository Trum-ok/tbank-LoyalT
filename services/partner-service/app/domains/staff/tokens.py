"""Подпись/проверка токена кассира поверх app.jwt_tokens."""

from uuid import UUID

from app import jwt_tokens
from app.config import get_settings

settings = get_settings()

TOKEN_TYPE = "staff"


def issue(staff_id: UUID, partner_id: UUID) -> str:
    return jwt_tokens.encode(
        {"sub": str(staff_id), "pid": str(partner_id), "typ": TOKEN_TYPE},
        secret=settings.jwt_secret,
        ttl_seconds=settings.jwt_ttl_hours * 3600,
    )


def parse(token: str) -> tuple[UUID, UUID]:
    """Возвращает (staff_id, partner_id). Бросает jwt_tokens.TokenError."""
    payload = jwt_tokens.decode(token, secret=settings.jwt_secret)
    if payload.get("typ") != TOKEN_TYPE:
        raise jwt_tokens.TokenError("Not a staff token")
    return UUID(str(payload["sub"])), UUID(str(payload["pid"]))
