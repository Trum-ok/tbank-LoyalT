"""Сквозной идентификатор запроса (request_id) в contextvars.

Один и тот же id живёт в рамках HTTP-запроса, прокидывается в Kafka-конверт
и восстанавливается на стороне consumer'а — так логи 4 сервисов связываются
в единую трассу без внешнего трейсинга.
"""

from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return request_id_ctx.get()


def set_request_id(value: str | None) -> str:
    """Ставит request_id (или генерирует новый, если пусто). Возвращает итог."""
    rid = value or new_request_id()
    request_id_ctx.set(rid)
    return rid


def new_request_id() -> str:
    return uuid4().hex
