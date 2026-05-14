from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domains.notifications.models import DeliveryStatus, NotificationType


class NotificationCreate(BaseModel):
    customer_id: UUID
    type: NotificationType
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=1000)
    payload: dict[str, Any] = Field(default_factory=dict)


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    type: NotificationType
    title: str
    body: str
    payload: dict[str, Any]
    delivery_status: DeliveryStatus
    delivered_at: datetime | None
    delivery_error: str | None
    is_read: bool
    created_at: datetime
