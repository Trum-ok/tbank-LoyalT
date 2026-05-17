from uuid import UUID

from fastapi import APIRouter, Query, status
from loyalt_common import error_responses

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


@router.get(
    "/categories",
    response_model=list[CategoryRead],
    summary="Список категорий каталога",
    responses=error_responses(401, 403),
)
async def list_categories(_: CurrentAdmin, session: SessionDep) -> list[CategoryRead]:
    """Переопределения категорий витрины. 401/403 — проблема с
    авторизацией админа."""
    items = await service.list_categories(session)
    return [CategoryRead.model_validate(i) for i in items]


@router.put(
    "/categories/{code}",
    response_model=CategoryRead,
    summary="Создать/обновить категорию",
    responses=error_responses(401, 403, 404),
)
async def upsert_category(
    code: str,
    data: CategoryUpsert,
    _: CurrentAdmin,
    session: SessionDep,
) -> CategoryRead:
    """Создаёт или обновляет переопределение категории по её коду.
    Код должен быть из допустимого набора. 401/403 — проблема с
    авторизацией админа; 404 — неизвестный код категории.
    """
    category = await service.upsert_category(session, code, data)
    return CategoryRead.model_validate(category)


# --- featured partners ---


@router.get(
    "/featured",
    response_model=list[FeaturedPartnerRead],
    summary="Список избранных партнёров",
    responses=error_responses(401, 403),
)
async def list_featured(
    _: CurrentAdmin, session: SessionDep
) -> list[FeaturedPartnerRead]:
    """Партнёры, закреплённые в витрине. 401/403 — проблема с
    авторизацией админа."""
    items = await service.list_featured(session)
    return [FeaturedPartnerRead.model_validate(i) for i in items]


@router.post(
    "/featured",
    response_model=FeaturedPartnerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить избранного партнёра",
    responses=error_responses(401, 403, 409),
)
async def add_featured(
    data: FeaturedPartnerCreate,
    _: CurrentAdmin,
    session: SessionDep,
) -> FeaturedPartnerRead:
    """Закрепляет партнёра в витрине на заданной позиции и в окне дат.
    401/403 — проблема с авторизацией админа; 409 — партнёр уже в
    избранном.
    """
    featured = await service.add_featured(session, data)
    return FeaturedPartnerRead.model_validate(featured)


@router.delete(
    "/featured/{featured_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Убрать избранного партнёра",
    responses=error_responses(401, 403, 404),
)
async def remove_featured(
    featured_id: UUID, _: CurrentAdmin, session: SessionDep
) -> None:
    """Снимает партнёра с витрины. 401/403 — проблема с авторизацией
    админа; 404 — запись избранного не найдена."""
    await service.remove_featured(session, featured_id)


# --- banners ---


@router.get(
    "/banners",
    response_model=list[BannerRead],
    summary="Список баннеров",
    responses=error_responses(401, 403),
)
async def list_banners(
    _: CurrentAdmin,
    session: SessionDep,
    active_only: bool = Query(default=False),
) -> list[BannerRead]:
    """Рекламные баннеры витрины. `active_only` оставляет только
    активные. 401/403 — проблема с авторизацией админа."""
    items = await service.list_banners(session, active_only=active_only)
    return [BannerRead.model_validate(i) for i in items]


@router.post(
    "/banners",
    response_model=BannerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать баннер",
    responses=error_responses(401, 403),
)
async def create_banner(
    data: BannerCreate, _: CurrentAdmin, session: SessionDep
) -> BannerRead:
    """Создаёт рекламный баннер для витрины. 401/403 — проблема с
    авторизацией админа."""
    banner = await service.create_banner(session, data)
    return BannerRead.model_validate(banner)


@router.patch(
    "/banners/{banner_id}",
    response_model=BannerRead,
    summary="Изменить баннер",
    responses=error_responses(401, 403, 404),
)
async def update_banner(
    banner_id: UUID,
    data: BannerUpdate,
    _: CurrentAdmin,
    session: SessionDep,
) -> BannerRead:
    """Частично обновляет баннер. 401/403 — проблема с авторизацией
    админа; 404 — баннер не найден."""
    banner = await service.update_banner(session, banner_id, data)
    return BannerRead.model_validate(banner)


@router.delete(
    "/banners/{banner_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить баннер",
    responses=error_responses(401, 403, 404),
)
async def delete_banner(banner_id: UUID, _: CurrentAdmin, session: SessionDep) -> None:
    """Удаляет баннер. 401/403 — проблема с авторизацией админа;
    404 — баннер не найден."""
    await service.delete_banner(session, banner_id)
