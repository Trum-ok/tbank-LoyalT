import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

SERVICE_ROOT = Path(__file__).parents[2] / "services" / "admin-service"
sys.path.insert(0, str(SERVICE_ROOT))

from app.domains.catalog import service  # noqa: E402
from app.domains.catalog.schemas import (  # noqa: E402
    BannerCreate,
    BannerUpdate,
    CategoryUpsert,
    FeaturedPartnerCreate,
)
from app.errors import ConflictError, NotFoundError  # noqa: E402


class TestCategories:
    async def test_upsert_unknown_code_raises(self, session: AsyncSession):
        with pytest.raises(NotFoundError, match="Unknown category"):
            await service.upsert_category(
                session, "spaceships", CategoryUpsert(label="X")
            )

    async def test_upsert_creates_then_updates(self, session: AsyncSession):
        created = await service.upsert_category(
            session, "food", CategoryUpsert(label="Еда", display_order=1)
        )
        assert created.label == "Еда"

        updated = await service.upsert_category(
            session, "food", CategoryUpsert(label="Рестораны", display_order=2)
        )
        assert updated.label == "Рестораны"
        assert len(await service.list_categories(session)) == 1


class TestFeaturedPartners:
    async def test_add_and_list(self, session: AsyncSession):
        await service.add_featured(
            session, FeaturedPartnerCreate(partner_id=uuid4(), position=1)
        )
        assert len(await service.list_featured(session)) == 1

    async def test_duplicate_partner_conflicts(self, session: AsyncSession):
        pid = uuid4()
        await service.add_featured(session, FeaturedPartnerCreate(partner_id=pid))
        with pytest.raises(ConflictError, match="already featured"):
            await service.add_featured(session, FeaturedPartnerCreate(partner_id=pid))

    async def test_remove_missing_raises(self, session: AsyncSession):
        with pytest.raises(NotFoundError):
            await service.remove_featured(session, uuid4())


class TestBanners:
    async def test_create_and_active_only_filter(self, session: AsyncSession):
        await service.create_banner(
            session, BannerCreate(title="Активный", is_active=True)
        )
        await service.create_banner(
            session, BannerCreate(title="Выключенный", is_active=False)
        )

        assert len(await service.list_banners(session)) == 2
        active = await service.list_banners(session, active_only=True)
        assert [b.title for b in active] == ["Активный"]

    async def test_update_banner(self, session: AsyncSession):
        banner = await service.create_banner(session, BannerCreate(title="Старый"))
        updated = await service.update_banner(
            session, banner.id, BannerUpdate(title="Новый")
        )
        assert updated.title == "Новый"

    async def test_delete_missing_raises(self, session: AsyncSession):
        with pytest.raises(NotFoundError):
            await service.delete_banner(session, uuid4())
