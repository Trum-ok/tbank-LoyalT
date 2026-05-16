"""
Тестовая инфраструктура для core-service.

Использует реальный PostgreSQL из docker-compose (localhost:5433).
Схема test_core создаётся один раз на сессию, очищается между тестами
через TRUNCATE ... CASCADE, чтобы тесты не мешали друг другу.
"""

import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

SERVICE_ROOT = Path(__file__).parents[2] / "services" / "core-service"
sys.path.insert(0, str(SERVICE_ROOT))

# Устанавливаем env до любого импорта app.*, чтобы lru_cached settings
# прочитали правильный URL (engine создаётся лениво — реального подключения нет).
os.environ.setdefault(
    "CORE_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5433/tbank_loyalt",
)
os.environ.setdefault("CORE_KAFKA_ENABLED", "false")

from app.database import Base  # noqa: E402
from app.domains.partners.models import Partner, PartnerCategory, PartnerStatus  # noqa: E402

TEST_SCHEMA = "test_core"
TEST_DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5433/tbank_loyalt"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Движок с тестовой схемой; схема создаётся/сносится один раз за сессию."""
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        execution_options={"schema_translate_map": {"core": TEST_SCHEMA}},
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
    """Сессия к тестовой схеме; после каждого теста чистим таблицы."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as sess:
        yield sess
        # Очищаем в правильном порядке, CASCADE снимает зависимости FK
        await sess.execute(text(f"TRUNCATE {TEST_SCHEMA}.program_tier CASCADE"))
        await sess.execute(text(f"TRUNCATE {TEST_SCHEMA}.program CASCADE"))
        await sess.execute(text(f"TRUNCATE {TEST_SCHEMA}.partner CASCADE"))
        await sess.commit()


@pytest_asyncio.fixture
async def partner_id(session: AsyncSession) -> UUID:
    """Создаёт партнёра и возвращает его id."""
    pid = uuid4()
    partner = Partner(
        id=pid,
        inn="1234567890",
        name="Test Coffee",
        category=PartnerCategory.FOOD,
        logo_url=None,
        brand_color=None,
        status=PartnerStatus.ACTIVE,
    )
    session.add(partner)
    await session.commit()
    return pid
