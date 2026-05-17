"""Publisher событий core-service.

Тот же контракт, что в partner-service: envelope `{type, occurred_at, payload}`.
При выключенной Kafka события сериализуются и логируются.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from aiokafka import AIOKafkaProducer
from loyalt_common import with_request_id

from app.config import get_settings

logger = logging.getLogger("core.events")


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
        envelope = with_request_id(
            {
                "type": event_type,
                "occurred_at": datetime.now(UTC).isoformat(),
                "payload": payload,
            }
        )
        if self._producer is None:
            logger.info(
                "event(stub) topic=%s key=%s body=%s",
                self._settings.kafka_topic_core_events,
                key,
                json.dumps(envelope, cls=_UUIDEncoder, ensure_ascii=False),
            )
            return
        await self._producer.send_and_wait(
            self._settings.kafka_topic_core_events,
            value=envelope,
            key=key,
        )


publisher = EventPublisher()
