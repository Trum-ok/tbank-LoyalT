"""ASGI-middleware: request_id на каждый HTTP-запрос.

Берёт `X-Request-ID` из входящего запроса (если клиент/гейтвей его прислал),
иначе генерирует новый; кладёт в contextvar и возвращает в ответе тем же
заголовком. Чистый ASGI — без подводных камней BaseHTTPMiddleware.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from loyalt_common.context import request_id_ctx, set_request_id

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

_HEADER = b"x-request-id"


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = None
        for key, value in scope.get("headers", []):
            if key == _HEADER:
                incoming = value.decode("latin-1")
                break

        rid = set_request_id(incoming)
        token = request_id_ctx.set(rid)

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((_HEADER, rid.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            request_id_ctx.reset(token)
