"""Проброс request_id через Kafka-конверт событий.

Контракт конверта (`{type, occurred_at, payload}`) расширяется опциональным
ключом `request_id` — обратносовместимо: старые сообщения без него consumer
обработает, просто сгенерировав новый id.
"""

from __future__ import annotations

from typing import Any

from loyalt_common.context import get_request_id, set_request_id

FIELD = "request_id"


def with_request_id(envelope: dict[str, Any]) -> dict[str, Any]:
    """Добавляет в конверт текущий request_id (если он есть в контексте)."""
    rid = get_request_id()
    if rid:
        envelope[FIELD] = rid
    return envelope


def bind_request_id(envelope: dict[str, Any]) -> str:
    """Восстанавливает request_id из конверта в контекст consumer'а.

    Нет ключа (старое сообщение) → генерируется новый id, трасса не рвётся.
    """
    return set_request_id(envelope.get(FIELD))
