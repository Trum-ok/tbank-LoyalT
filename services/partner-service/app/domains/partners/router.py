from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from loyalt_common import error_responses

from app import storage
from app.config import get_settings
from app.deps import CurrentAccountId, CurrentAdminId, SessionDep
from app.domains.partners import service
from app.domains.partners.models import PartnerStatus
from app.domains.partners.schemas import PartnerRead, PartnerUpdate

partner_router = APIRouter(prefix="/partners", tags=["partners"])
admin_router = APIRouter(prefix="/admin/partners", tags=["partners-admin"])


@partner_router.get(
    "/me",
    response_model=PartnerRead,
    summary="Мой профиль партнёра",
    responses=error_responses(404),
)
async def get_my_partner(
    account_id: CurrentAccountId, session: SessionDep
) -> PartnerRead:
    """Карточка партнёра текущего аккаунта. 404 — партнёр не найден
    (заявка ещё не одобрена)."""
    partner = await service.get_partner_by_account(session, account_id)
    return PartnerRead.model_validate(partner)


@partner_router.patch(
    "/me",
    response_model=PartnerRead,
    summary="Обновить профиль партнёра",
    responses=error_responses(404),
)
async def update_my_partner(
    data: PartnerUpdate,
    account_id: CurrentAccountId,
    session: SessionDep,
) -> PartnerRead:
    """Меняет название/контакты/брендирование, публикует `partner.updated`.
    404 — партнёр не найден."""
    partner = await service.update_partner_profile(session, account_id, data)
    return PartnerRead.model_validate(partner)


@partner_router.put(
    "/me/logo",
    response_model=PartnerRead,
    summary="Загрузить логотип партнёра",
    responses=error_responses(400, 404),
)
async def upload_my_logo(
    account_id: CurrentAccountId,
    session: SessionDep,
    file: UploadFile = File(...),
) -> PartnerRead:
    """Загрузить кастомный логотип (PNG/JPEG/WebP) в MinIO.

    Файл кладётся в публичный bucket, `logo_url` проставляется на прямую
    ссылку — каталог клиента покажет аватар вместо инициалов. Тип
    проверяется по содержимому, не по заголовку (SVG не поддерживается:
    риск XSS). 400 — пустой файл; 404 — партнёр не найден;
    415 — неподдерживаемый тип файла; 413 — файл больше лимита.
    """
    settings = get_settings()
    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пустой файл",
        )
    if len(data) > settings.logo_max_bytes:
        limit_mb = settings.logo_max_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Файл больше {limit_mb:.0f} МБ",
        )

    # partner_id нужен как стабильный ключ объекта в хранилище.
    partner = await service.get_partner_by_account(session, account_id)
    try:
        # Тип определяется по сигнатуре байтов внутри upload_logo —
        # клиентскому Content-Type не доверяем (вектор stored XSS).
        logo_url = await storage.upload_logo(partner.id, data)
    except storage.UnsupportedImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Поддерживаются только PNG, JPEG и WebP",
        ) from exc
    partner = await service.set_logo_url(session, account_id, logo_url)
    return PartnerRead.model_validate(partner)


@admin_router.get(
    "",
    response_model=list[PartnerRead],
    summary="Список партнёров",
)
async def list_partners(
    session: SessionDep,
    _admin: CurrentAdminId,
    status_filter: PartnerStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PartnerRead]:
    """Реестр партнёров для панели Т-Банка с фильтром по статусу."""
    partners = await service.list_partners(
        session, status_filter=status_filter, limit=limit, offset=offset
    )
    return [PartnerRead.model_validate(p) for p in partners]


@admin_router.get(
    "/{partner_id}",
    response_model=PartnerRead,
    summary="Карточка партнёра",
    responses=error_responses(404),
)
async def get_partner(
    partner_id: UUID, session: SessionDep, _admin: CurrentAdminId
) -> PartnerRead:
    """Детали партнёра по id. 404 — партнёр не найден."""
    partner = await service.get_partner(session, partner_id)
    return PartnerRead.model_validate(partner)


@admin_router.post(
    "/{partner_id}/suspend",
    response_model=PartnerRead,
    summary="Приостановить партнёра",
    responses=error_responses(404),
)
async def suspend_partner(
    partner_id: UUID, session: SessionDep, _admin: CurrentAdminId
) -> PartnerRead:
    """Переводит партнёра в статус suspended. 404 — партнёр не найден."""
    partner = await service.set_status(session, partner_id, PartnerStatus.SUSPENDED)
    return PartnerRead.model_validate(partner)


@admin_router.post(
    "/{partner_id}/block",
    response_model=PartnerRead,
    summary="Заблокировать партнёра",
    responses=error_responses(404),
)
async def block_partner(
    partner_id: UUID, session: SessionDep, _admin: CurrentAdminId
) -> PartnerRead:
    """Блокирует партнёра (статус blocked). 404 — партнёр не найден."""
    partner = await service.set_status(session, partner_id, PartnerStatus.BLOCKED)
    return PartnerRead.model_validate(partner)


@admin_router.post(
    "/{partner_id}/unblock",
    response_model=PartnerRead,
    summary="Разблокировать партнёра",
    responses=error_responses(404),
)
async def unblock_partner(
    partner_id: UUID, session: SessionDep, _admin: CurrentAdminId
) -> PartnerRead:
    """Возвращает партнёра в статус active. 404 — партнёр не найден."""
    partner = await service.set_status(session, partner_id, PartnerStatus.ACTIVE)
    return PartnerRead.model_validate(partner)
