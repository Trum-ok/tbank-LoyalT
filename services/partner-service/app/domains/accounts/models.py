from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampsMixin, UUIDPKMixin


class Account(UUIDPKMixin, TimestampsMixin, Base):
    """Учётная запись партнёра в ЛК.

    На текущем этапе используется без пароля/JWT — идентификатор аккаунта
    передаётся в заголовке X-Account-Id. Когда подключим реальный auth
    (email/пароль или phone+OTP), сюда добавится `password_hash` и/или
    `phone`, и появятся ручки login/refresh.
    """

    __tablename__ = "account"

    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
