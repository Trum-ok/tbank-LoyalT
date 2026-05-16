from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app import storage
from app.config import get_settings
from app.deps import CurrentAccountId, CurrentAdminId, SessionDep
from app.domains.partners import service
from app.domains.partners.models import PartnerStatus
from app.domains.partners.schemas import PartnerRead, PartnerUpdate

partner_router = APIRouter(prefix="/partners", tags=["partners"])
admin_router = APIRouter(prefix="/admin/partners", tags=["partners-admin"])


@partner_router.get("/me", response_model=PartnerRead)
async def get_my_partner(
    account_id: CurrentAccountId, session: SessionDep
) -> PartnerRead:
    partner = await service.get_partner_by_account(session, account_id)
    return PartnerRead.model_validate(partner)


@partner_router.patch("/me", response_model=PartnerRead)
async def update_my_partner(
    data: PartnerUpdate,
    account_id: CurrentAccountId,
    session: SessionDep,
) -> PartnerRead:
    partner = await service.update_partner_profile(session, account_id, data)
    return PartnerRead.model_validate(partner)


@partner_router.put("/me/logo", response_model=PartnerRead)
async def upload_my_logo(
    account_id: CurrentAccountId,
    session: SessionDep,
    file: UploadFile = File(...),
) -> PartnerRead:
    """Загрузить кастомный логотип (PNG/SVG/JPEG/WebP) в MinIO.

    Файл кладётся в публичный bucket, `logo_url` проставляется на прямую
    ссылку — каталог клиента покажет аватар вместо инициалов.
    """
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in storage.EXT_BY_CONTENT_TYPE:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Поддерживаются только PNG, SVG, JPEG и WebP",
        )

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
    logo_url = await storage.upload_logo(partner.id, data, content_type)
    partner = await service.set_logo_url(session, account_id, logo_url)
    return PartnerRead.model_validate(partner)


@admin_router.get("", response_model=list[PartnerRead])
async def list_partners(
    session: SessionDep,
    _admin: CurrentAdminId,
    status_filter: PartnerStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PartnerRead]:
    partners = await service.list_partners(
        session, status_filter=status_filter, limit=limit, offset=offset
    )
    return [PartnerRead.model_validate(p) for p in partners]


@admin_router.get("/{partner_id}", response_model=PartnerRead)
async def get_partner(
    partner_id: UUID, session: SessionDep, _admin: CurrentAdminId
) -> PartnerRead:
    partner = await service.get_partner(session, partner_id)
    return PartnerRead.model_validate(partner)


@admin_router.post("/{partner_id}/suspend", response_model=PartnerRead)
async def suspend_partner(
    partner_id: UUID, session: SessionDep, _admin: CurrentAdminId
) -> PartnerRead:
    partner = await service.set_status(session, partner_id, PartnerStatus.SUSPENDED)
    return PartnerRead.model_validate(partner)


@admin_router.post("/{partner_id}/block", response_model=PartnerRead)
async def block_partner(
    partner_id: UUID, session: SessionDep, _admin: CurrentAdminId
) -> PartnerRead:
    partner = await service.set_status(session, partner_id, PartnerStatus.BLOCKED)
    return PartnerRead.model_validate(partner)


@admin_router.post("/{partner_id}/unblock", response_model=PartnerRead)
async def unblock_partner(
    partner_id: UUID, session: SessionDep, _admin: CurrentAdminId
) -> PartnerRead:
    partner = await service.set_status(session, partner_id, PartnerStatus.ACTIVE)
    return PartnerRead.model_validate(partner)
