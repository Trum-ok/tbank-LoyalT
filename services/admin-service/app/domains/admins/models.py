from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampsMixin, UUIDPKMixin


class AdminAccount(UUIDPKMixin, TimestampsMixin, Base):
    """Сотрудник Т-Банка с доступом к админ-панели."""

    __tablename__ = "admin_account"

    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
