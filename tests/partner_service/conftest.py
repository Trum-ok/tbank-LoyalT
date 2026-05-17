"""Фикстуры partner-service.

ВАЖНО: все сервисы используют пакет верхнего уровня `app`, поэтому тесты
разных сервисов нельзя запускать в одном процессе pytest (sys.modules
закэширует первый импортированный `app`). Запуск — по одному сервису на
процесс (см. цель `test` в Makefile).
"""

import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

SERVICE_ROOT = Path(__file__).parents[2] / "services" / "partner-service"
sys.path.insert(0, str(SERVICE_ROOT))

# Должно быть выставлено до любого импорта app.* — lru_cache настроек
# подхватит правильный URL и отключённую Kafka.
os.environ.setdefault(
    "PARTNER_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5433/tbank_loyalt",
)
os.environ.setdefault("PARTNER_KAFKA_ENABLED", "false")
# Явный тестовый секрет: тесты идут с debug=False, поэтому дефолтный
# sentinel привёл бы к фейл-фасту в Settings.
os.environ.setdefault("PARTNER_JWT_SECRET", "test-jwt-secret")

import app.models  # noqa: F401, E402 — регистрирует все ORM-модели в Base.metadata
from app.database import Base  # noqa: E402
from app.domains.accounts.models import Account  # noqa: E402

TEST_SCHEMA = "test_partner"
TEST_DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5433/tbank_loyalt"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        execution_options={"schema_translate_map": {"partner": TEST_SCHEMA}},
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
async def account(session: AsyncSession) -> Account:
    acc = Account(
        id=uuid4(),
        email="owner@coffee.ru",
        full_name="Иван Петров",
        phone="+79001234567",
    )
    session.add(acc)
    await session.commit()
    await session.refresh(acc)
    return acc


@pytest_asyncio.fixture
async def account_id(account: Account) -> UUID:
    return account.id
