"""Минимальный HS256-JWT на stdlib (без PyJWT — в зависимостях его нет).

Используется для токенов кассира: partner-service подписывает на
`/staff/login`, partner-service и core-service проверяют подпись общим
секретом. В dev секрет одинаковый по умолчанию в обоих сервисах; в
проде задаётся через PARTNER_JWT_SECRET / CORE_JWT_SECRET (значения
должны совпадать).
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any

ALG = "HS256"


class TokenError(Exception):
    """Невалидный/просроченный токен."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def encode(payload: dict[str, Any], secret: str, ttl_seconds: int) -> str:
    now = int(time.time())
    body = {**payload, "iat": now, "exp": now + ttl_seconds}
    header = {"alg": ALG, "typ": "JWT"}
    segments = [
        _b64url_encode(json.dumps(header, separators=(",", ":")).encode()),
        _b64url_encode(json.dumps(body, separators=(",", ":")).encode()),
    ]
    signing_input = ".".join(segments).encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    segments.append(_b64url_encode(sig))
    return ".".join(segments)


def decode(token: str, secret: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError as exc:
        raise TokenError("Malformed token") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    try:
        given = _b64url_decode(sig_b64)
    except Exception as exc:
        raise TokenError("Bad signature encoding") from exc
    if not hmac.compare_digest(expected, given):
        raise TokenError("Invalid signature")

    try:
        payload: dict[str, Any] = json.loads(_b64url_decode(payload_b64))
    except Exception as exc:
        raise TokenError("Bad payload") from exc
    if int(payload.get("exp", 0)) < int(time.time()):
        raise TokenError("Token expired")
    return payload
