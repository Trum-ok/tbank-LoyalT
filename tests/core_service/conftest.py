import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

SERVICE_ROOT = Path(__file__).parents[2] / "services" / "core-service"
sys.path.insert(0, str(SERVICE_ROOT))

# Must be set before any app.* import so lru_cached settings pick up the right URL.
os.environ.setdefault(
    "CORE_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5433/tbank_loyalt",
)
os.environ.setdefault("CORE_KAFKA_ENABLED", "false")

import app.models  # noqa: F401, E402 — registers all ORM models in Base.metadata
from app.database import Base  # noqa: E402
from app.domains.enrollments.models import Customer, Enrollment  # noqa: E402
from app.domains.partners.models import (  # noqa: E402
    Partner,
    PartnerCategory,
    PartnerStatus,
)
from app.domains.programs import service as program_service  # noqa: E402
from app.domains.programs.models import ProgramStatus, ProgramType  # noqa: E402
from app.domains.programs.schemas import ProgramCreate  # noqa: E402

TEST_SCHEMA = "test_core"
TEST_DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5433/tbank_loyalt"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
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
    factory = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with factory() as sess:
        yield sess
        for table in (
            "bonus_trigger_log",
            "bonus_trigger",
            "transaction",
            "enrollment",
            "customer",
            "program_tier",
            "program",
            "partner",
        ):
            await sess.execute(
                text(f"TRUNCATE {TEST_SCHEMA}.{table} CASCADE")
            )
        await sess.commit()


@pytest_asyncio.fixture
async def partner_id(session: AsyncSession) -> UUID:
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


@pytest_asyncio.fixture
async def program(session: AsyncSession, partner_id: UUID):
    return await program_service.create_program(
        session,
        partner_id,
        ProgramCreate(
            name="Тест",
            type=ProgramType.ACCRUAL,
            accrual_rule={"percent": 5},
        ),
    )


@pytest_asyncio.fixture
async def published_program(session: AsyncSession, partner_id: UUID):
    p = await program_service.create_program(
        session,
        partner_id,
        ProgramCreate(name="Опубликованная", type=ProgramType.ACCRUAL, accrual_rule={"percent": 5}),
    )
    return await program_service.transition_status(
        session, p.id, partner_id, ProgramStatus.PUBLISHED
    )


@pytest_asyncio.fixture
async def customer_id(session: AsyncSession) -> UUID:
    cid = uuid4()
    customer = Customer(id=cid)
    session.add(customer)
    await session.commit()
    return cid


@pytest_asyncio.fixture
async def enrollment(session: AsyncSession, published_program, customer_id: UUID):
    e = Enrollment(
        customer_id=customer_id,
        program_id=published_program.id,
        short_code="1000",
    )
    session.add(e)
    await session.commit()
    await session.refresh(e)
    return e
