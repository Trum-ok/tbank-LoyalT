from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domains.broadcasts.models import BroadcastSegment, BroadcastStatus


class BroadcastBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=1000)
    segment: BroadcastSegment = BroadcastSegment.ALL_ENROLLED
    program_id: UUID | None = None

    @model_validator(mode="after")
    def _check_program(self) -> "BroadcastBase":
        if self.segment == BroadcastSegment.BY_PROGRAM and self.program_id is None:
            raise ValueError("program_id обязателен для сегмента by_program")
        return self


class BroadcastCreate(BroadcastBase):
    pass


class BroadcastUpdate(BaseModel):
    """Частичное обновление черновика."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1, max_length=1000)
    segment: BroadcastSegment | None = None
    program_id: UUID | None = None


class BroadcastRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    partner_id: UUID
    title: str
    body: str
    segment: BroadcastSegment
    program_id: UUID | None
    status: BroadcastStatus
    audience_count: int | None
    sent_count: int | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AudiencePreview(BaseModel):
    count: int
