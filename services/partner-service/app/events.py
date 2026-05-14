"""Publisher событий партнёрского сервиса.

Если `kafka_enabled=False`, события сериализуются и логируются — это
позволяет работать без поднятой Kafka локально. Контракт сообщений (имена
типов, payload) одинаковый в обоих режимах, чтобы при включении Kafka
ничего не пришлось переделывать.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from aiokafka import AIOKafkaProducer

from app.config import get_settings

logger = logging.getLogger("partner.events")


class _UUIDEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, UUID):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


class EventPublisher:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        if not self._settings.kafka_enabled:
            logger.info("Kafka disabled, EventPublisher running in stub mode")
            return
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, cls=_UUIDEncoder).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        key: str | None = None,
    ) -> None:
        envelope = {
            "type": event_type,
            "occurred_at": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
        if self._producer is None:
            logger.info(
                "event(stub) topic=%s key=%s body=%s",
                self._settings.kafka_topic_partner_events,
                key,
                json.dumps(envelope, cls=_UUIDEncoder, ensure_ascii=False),
            )
            return
        await self._producer.send_and_wait(
            self._settings.kafka_topic_partner_events,
            value=envelope,
            key=key,
        )


publisher = EventPublisher()
