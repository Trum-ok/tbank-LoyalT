from collections.abc import AsyncIterator
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

from app.config import get_settings

settings = get_settings()


def _make_engine(url: str):
    return create_async_engine(
        url,
        echo=settings.db_echo,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
    )


engine = _make_engine(settings.database_url)

# Read-реплика для тяжёлых read-only запросов. Если DSN не задан —
# переиспользуем primary, чтобы код выше не зависел от наличия реплики.
read_engine = (
    _make_engine(settings.database_replica_url)
    if settings.database_replica_url
    else engine
)

SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

ReadSessionLocal = async_sessionmaker(
    read_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


metadata = MetaData(schema=settings.db_schema)


class Base(DeclarativeBase):
    metadata = metadata


class UUIDPKMixin:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class TimestampsMixin:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_read_session() -> AsyncIterator[AsyncSession]:
    """Сессия к read-реплике (или primary, если реплика не настроена).

    Только для идемпотентных read-only запросов: история транзакций,
    аналитика. Реплика отстаёт от primary — нельзя использовать там,
    где сразу после записи нужно прочитать свежие данные.
    """
    async with ReadSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
