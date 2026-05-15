from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampsMixin, UUIDPKMixin


class Staff(UUIDPKMixin, TimestampsMixin, Base):
    """Учётка кассира/официанта точки партнёра.

    Кассир работает в контексте своего `partner_id` — он передаётся в
    core-service как X-Partner-Id для начисления/списания баллов. Полноценной
    авторизации (JWT/сессии) пока нет: вход по паре `login_code` + PIN, дальше
    клиент кассы хранит staff_id/partner_id у себя.
    """

    __tablename__ = "staff"
    __table_args__ = (Index("ix_staff_partner_id", "partner_id"),)

    partner_id: Mapped[UUID] = mapped_column(
        ForeignKey("partner.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    # Короткий человекочитаемый код точки/смены, по которому кассир входит.
    login_code: Mapped[str] = mapped_column(String(32), unique=True)
    pin_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
