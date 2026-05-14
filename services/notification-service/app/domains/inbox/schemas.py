from typing import Any

from pydantic import BaseModel, Field


class IncomingEvent(BaseModel):
    """Конверт события из Kafka/HTTP.

    Контракт сейчас совпадает с тем, что публикует partner-service в
    `EventPublisher.publish`. Когда core добавит publisher, события из
    `core.events` придут в том же формате.
    """

    type: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
