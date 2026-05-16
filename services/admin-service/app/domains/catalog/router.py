from uuid import UUID

from fastapi import APIRouter, Query, status

from app.deps import CurrentAdmin, SessionDep
from app.domains.catalog import service
from app.domains.catalog.schemas import (
    BannerCreate,
    BannerRead,
    BannerUpdate,
    CategoryRead,
    CategoryUpsert,
    FeaturedPartnerCreate,
    FeaturedPartnerRead,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


# --- categories ---


@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(_: CurrentAdmin, session: SessionDep) -> list[CategoryRead]:
    items = await service.list_categories(session)
    return [CategoryRead.model_validate(i) for i in items]


@router.put("/categories/{code}", response_model=CategoryRead)
async def upsert_category(
    code: str,
    data: CategoryUpsert,
    _: CurrentAdmin,
    session: SessionDep,
) -> CategoryRead:
    category = await service.upsert_category(session, code, data)
    return CategoryRead.model_validate(category)


# --- featured partners ---


@router.get("/featured", response_model=list[FeaturedPartnerRead])
async def list_featured(
    _: CurrentAdmin, session: SessionDep
) -> list[FeaturedPartnerRead]:
    items = await service.list_featured(session)
    return [FeaturedPartnerRead.model_validate(i) for i in items]


@router.post(
    "/featured",
    response_model=FeaturedPartnerRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_featured(
    data: FeaturedPartnerCreate,
    _: CurrentAdmin,
    session: SessionDep,
) -> FeaturedPartnerRead:
    featured = await service.add_featured(session, data)
    return FeaturedPartnerRead.model_validate(featured)


@router.delete("/featured/{featured_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_featured(
    featured_id: UUID, _: CurrentAdmin, session: SessionDep
) -> None:
    await service.remove_featured(session, featured_id)


# --- banners ---


@router.get("/banners", response_model=list[BannerRead])
async def list_banners(
    _: CurrentAdmin,
    session: SessionDep,
    active_only: bool = Query(default=False),
) -> list[BannerRead]:
    items = await service.list_banners(session, active_only=active_only)
    return [BannerRead.model_validate(i) for i in items]


@router.post("/banners", response_model=BannerRead, status_code=status.HTTP_201_CREATED)
async def create_banner(
    data: BannerCreate, _: CurrentAdmin, session: SessionDep
) -> BannerRead:
    banner = await service.create_banner(session, data)
    return BannerRead.model_validate(banner)


@router.patch("/banners/{banner_id}", response_model=BannerRead)
async def update_banner(
    banner_id: UUID,
    data: BannerUpdate,
    _: CurrentAdmin,
    session: SessionDep,
) -> BannerRead:
    banner = await service.update_banner(session, banner_id, data)
    return BannerRead.model_validate(banner)


@router.delete("/banners/{banner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_banner(banner_id: UUID, _: CurrentAdmin, session: SessionDep) -> None:
    await service.delete_banner(session, banner_id)
