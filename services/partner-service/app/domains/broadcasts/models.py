from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampsMixin, UUIDPKMixin


class BroadcastSegment(StrEnum):
    """Сегмент аудитории. Значения совпадают с core-service AudienceSegment."""

    ALL_ENROLLED = "all_enrolled"
    ACTIVE_30D = "active_30d"
    BY_PROGRAM = "by_program"
    BALANCE_POSITIVE = "balance_positive"
    NEW_7D = "new_7d"


class BroadcastStatus(StrEnum):
    DRAFT = "draft"  # черновик, ещё не отправлен
    SENT = "sent"  # отправлен (опубликовано событие фан-аута)
    FAILED = "failed"  # ошибка при отправке


class Broadcast(UUIDPKMixin, TimestampsMixin, Base):
    """Рассылка партнёра: черновик или отправленная."""

    __tablename__ = "broadcast"
    __table_args__ = (Index("ix_broadcast_partner_id", "partner_id"),)

    partner_id: Mapped[UUID] = mapped_column()
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(String(1000))

    segment: Mapped[BroadcastSegment] = mapped_column(
        String(32), default=BroadcastSegment.ALL_ENROLLED
    )
    # Только для segment = by_program.
    program_id: Mapped[UUID | None] = mapped_column()

    status: Mapped[BroadcastStatus] = mapped_column(
        String(16),
        default=BroadcastStatus.DRAFT,
        server_default=BroadcastStatus.DRAFT.value,
    )
    # Размер аудитории на момент отправки.
    audience_count: Mapped[int | None] = mapped_column()
    sent_count: Mapped[int | None] = mapped_column()
    sent_at: Mapped[datetime | None] = mapped_column()
