from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domains.devices.models import DevicePlatform


class DeviceRegister(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    platform: DevicePlatform


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    token: str
    platform: DevicePlatform
    is_active: bool
    created_at: datetime
    updated_at: datetime
