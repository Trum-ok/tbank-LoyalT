from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog.models import Banner, CategoryOverride, FeaturedPartner
from app.domains.catalog.schemas import (
    BannerCreate,
    BannerUpdate,
    CategoryUpsert,
    FeaturedPartnerCreate,
)
from app.errors import ConflictError, NotFoundError

ALLOWED_CATEGORY_CODES = {"food", "beauty", "retail", "services", "entertainment"}


# --- categories ---

async def upsert_category(
    session: AsyncSession, code: str, data: CategoryUpsert
) -> CategoryOverride:
    if code not in ALLOWED_CATEGORY_CODES:
        raise NotFoundError(f"Unknown category code: {code}")
    category = await session.get(CategoryOverride, code)
    if category is None:
        category = CategoryOverride(code=code, **data.model_dump())
        session.add(category)
    else:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(category, field, value)
    await session.commit()
    await session.refresh(category)
    return category


async def list_categories(session: AsyncSession) -> list[CategoryOverride]:
    result = await session.execute(
        select(CategoryOverride).order_by(CategoryOverride.display_order.asc())
    )
    return list(result.scalars().all())


# --- featured partners ---

async def add_featured(
    session: AsyncSession, data: FeaturedPartnerCreate
) -> FeaturedPartner:
    featured = FeaturedPartner(**data.model_dump())
    session.add(featured)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Partner is already featured") from exc
    await session.refresh(featured)
    return featured


async def list_featured(session: AsyncSession) -> list[FeaturedPartner]:
    result = await session.execute(
        select(FeaturedPartner).order_by(FeaturedPartner.position.asc())
    )
    return list(result.scalars().all())


async def remove_featured(session: AsyncSession, featured_id: UUID) -> None:
    featured = await session.get(FeaturedPartner, featured_id)
    if featured is None:
        raise NotFoundError("Featured partner not found")
    await session.delete(featured)
    await session.commit()


# --- banners ---

async def create_banner(session: AsyncSession, data: BannerCreate) -> Banner:
    banner = Banner(**data.model_dump())
    session.add(banner)
    await session.commit()
    await session.refresh(banner)
    return banner


async def list_banners(
    session: AsyncSession, active_only: bool = False
) -> list[Banner]:
    stmt = select(Banner)
    if active_only:
        stmt = stmt.where(Banner.is_active.is_(True))
    stmt = stmt.order_by(Banner.position.asc(), Banner.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_banner(
    session: AsyncSession, banner_id: UUID, data: BannerUpdate
) -> Banner:
    banner = await session.get(Banner, banner_id)
    if banner is None:
        raise NotFoundError("Banner not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(banner, field, value)
    await session.commit()
    await session.refresh(banner)
    return banner


async def delete_banner(session: AsyncSession, banner_id: UUID) -> None:
    banner = await session.get(Banner, banner_id)
    if banner is None:
        raise NotFoundError("Banner not found")
    await session.delete(banner)
    await session.commit()
