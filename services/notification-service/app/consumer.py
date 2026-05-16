"""Kafka consumer.

Подписывается на топики из `settings.kafka_topics`, разбирает конверт
`{type, payload, occurred_at?}` и передаёт в `inbox.handlers.handle_event`.
Если `kafka_enabled=False`, consumer не стартует — события можно
эмулировать через `POST /internal/events`.
"""

from __future__ import annotations

import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from app.config import get_settings
from app.database import SessionLocal
from app.domains.inbox.handlers import handle_event

logger = logging.getLogger("notification.consumer")


class EventConsumer:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if not self._settings.kafka_enabled:
            logger.info("Kafka disabled, EventConsumer is inactive")
            return
        self._consumer = AIOKafkaConsumer(
            *self._settings.kafka_topics,
            bootstrap_servers=self._settings.kafka_bootstrap_servers,
            group_id=self._settings.kafka_group_id,
            enable_auto_commit=False,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        await self._consumer.start()
        self._task = asyncio.create_task(self._run(), name="kafka-consumer")
        logger.info(
            "EventConsumer started, topics=%s group=%s",
            self._settings.kafka_topics,
            self._settings.kafka_group_id,
        )

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

    async def _run(self) -> None:
        assert self._consumer is not None
        try:
            async for msg in self._consumer:
                await self._process_message(msg)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Consumer loop crashed")

    async def _process_message(self, msg) -> None:  # type: ignore[no-untyped-def]
        assert self._consumer is not None
        envelope = msg.value or {}
        event_type = envelope.get("type")
        payload = envelope.get("payload") or {}
        if not event_type:
            logger.warning("Skip message without type: %s", envelope)
            await self._consumer.commit()
            return
        async with SessionLocal() as session:
            try:
                await handle_event(session, event_type, payload)
            except Exception:
                # Не коммитим оффсет — Kafka повторно доставит сообщение.
                logger.exception(
                    "Failed to process event type=%s offset=%s", event_type, msg.offset
                )
                return
        await self._consumer.commit()


consumer = EventConsumer()
