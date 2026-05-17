from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domains.devices.models import DevicePlatform


class DeviceRegister(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    platform: DevicePlatform

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "token": "fGzL9k2xQ1m:APA91bF8s7d6Example_push_token_value",
                    "platform": "ios",
                }
            ]
        }
    }


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    token: str
    platform: DevicePlatform
    is_active: bool
    created_at: datetime
    updated_at: datetime
