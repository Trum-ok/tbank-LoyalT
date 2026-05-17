"""Фикстуры notification-service.

ВАЖНО: пакет верхнего уровня называется `app` во всех сервисах — тесты
запускаются по одному сервису на процесс pytest (см. Makefile, цель `test`).
"""

import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

SERVICE_ROOT = Path(__file__).parents[2] / "services" / "notification-service"
sys.path.insert(0, str(SERVICE_ROOT))

os.environ.setdefault(
    "NOTIFICATION_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5433/tbank_loyalt",
)
os.environ.setdefault("NOTIFICATION_KAFKA_ENABLED", "false")

import app.models  # noqa: F401, E402 — регистрирует ORM-модели в Base.metadata
from app.database import Base  # noqa: E402
from app.domains.devices.models import Device, DevicePlatform  # noqa: E402

TEST_SCHEMA = "test_notification"
TEST_DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5433/tbank_loyalt"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        execution_options={"schema_translate_map": {"notification": TEST_SCHEMA}},
    )

    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {TEST_SCHEMA}"))
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {TEST_SCHEMA} CASCADE"))
    await engine.dispose()


@pytest_asyncio.fixture
async def session(test_engine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with factory() as sess:
        yield sess
        # Тест мог оставить транзакцию в aborted-состоянии — сбрасываем,
        # иначе TRUNCATE не выполнится и данные «протекут» в след. тест.
        await sess.rollback()
        rows = await sess.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = :s"),
            {"s": TEST_SCHEMA},
        )
        tables = [r[0] for r in rows]
        if tables:
            joined = ", ".join(f'{TEST_SCHEMA}."{t}"' for t in tables)
            await sess.execute(text(f"TRUNCATE {joined} RESTART IDENTITY CASCADE"))
        await sess.commit()


@pytest_asyncio.fixture
async def customer_id() -> UUID:
    return uuid4()


@pytest_asyncio.fixture
async def active_device(session: AsyncSession, customer_id: UUID) -> Device:
    device = Device(
        id=uuid4(),
        customer_id=customer_id,
        token="push-token-123456789",
        platform=DevicePlatform.IOS,
        is_active=True,
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)
    return device
