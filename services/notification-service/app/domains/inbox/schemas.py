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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "points_accrued",
                    "payload": {
                        "customer_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "points": 80,
                        "program_name": "Кофе Хауз",
                    },
                }
            ]
        }
    }
