from uuid import UUID

from fastapi import APIRouter, status
from loyalt_common import error_responses

from app.deps import CurrentAccountId, CurrentStaffId, SessionDep
from app.domains.partners.service import get_partner_by_account
from app.domains.staff import service, tokens
from app.domains.staff.schemas import (
    StaffCreate,
    StaffLoginRequest,
    StaffLoginResponse,
    StaffRead,
    StaffUpdate,
)

# Управление кассирами из ЛК партнёра (вход по X-Account-Id).
router = APIRouter(prefix="/staff", tags=["staff"])
# Вход кассы по коду + PIN (без авторизации).
auth_router = APIRouter(prefix="/staff", tags=["staff-auth"])


@auth_router.post(
    "/login",
    response_model=StaffLoginResponse,
    summary="Вход кассы",
    responses=error_responses(403, 404),
)
async def login(data: StaffLoginRequest, session: SessionDep) -> StaffLoginResponse:
    """Аутентификация кассира по коду и PIN, выдаёт JWT.

    Полученным `access_token` касса вызывает ручки начисления баллов в
    core-service. 403 — неверный код/PIN или сотрудник отключён;
    404 — у сотрудника не найден партнёр.
    """
    staff, partner = await service.authenticate(session, data.login_code, data.pin)
    return StaffLoginResponse(
        access_token=tokens.issue(staff.id, partner.id),
        token_type="bearer",
        staff_id=staff.id,
        staff_name=staff.name,
        partner_id=partner.id,
        partner_name=partner.name,
    )


@auth_router.get(
    "/me",
    response_model=StaffRead,
    summary="Текущий кассир",
    responses=error_responses(404),
)
async def get_me(staff_id: CurrentStaffId, session: SessionDep) -> StaffRead:
    """Профиль кассира по его JWT. 404 — сотрудник не найден."""
    staff = await service.get_staff(session, staff_id)
    return StaffRead.model_validate(staff)


@router.get(
    "",
    response_model=list[StaffRead],
    summary="Список кассиров партнёра",
    responses=error_responses(404),
)
async def list_staff(
    account_id: CurrentAccountId, session: SessionDep
) -> list[StaffRead]:
    """Все кассиры партнёра текущего аккаунта. 404 — партнёр не найден."""
    partner = await get_partner_by_account(session, account_id)
    rows = await service.list_staff(session, partner.id)
    return [StaffRead.model_validate(s) for s in rows]


@router.post(
    "",
    response_model=StaffRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать кассира",
    responses=error_responses(404, 409),
)
async def create_staff(
    data: StaffCreate, account_id: CurrentAccountId, session: SessionDep
) -> StaffRead:
    """Заводит кассира с кодом входа и PIN.

    404 — партнёр не найден; 409 — код входа `login_code` уже занят.
    """
    partner = await get_partner_by_account(session, account_id)
    staff = await service.create_staff(session, partner.id, data)
    return StaffRead.model_validate(staff)


@router.patch(
    "/{staff_id}",
    response_model=StaffRead,
    summary="Обновить кассира",
    responses=error_responses(403, 404),
)
async def update_staff(
    staff_id: UUID,
    data: StaffUpdate,
    account_id: CurrentAccountId,
    session: SessionDep,
) -> StaffRead:
    """Меняет имя/PIN/активность кассира.

    404 — партнёр или сотрудник не найден; 403 — сотрудник принадлежит
    другому партнёру.
    """
    partner = await get_partner_by_account(session, account_id)
    staff = await service.update_staff(session, staff_id, partner.id, data)
    return StaffRead.model_validate(staff)


@router.delete(
    "/{staff_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить кассира",
    responses=error_responses(403, 404),
)
async def delete_staff(
    staff_id: UUID, account_id: CurrentAccountId, session: SessionDep
) -> None:
    """Удаляет кассира партнёра.

    404 — партнёр или сотрудник не найден; 403 — сотрудник принадлежит
    другому партнёру.
    """
    partner = await get_partner_by_account(session, account_id)
    await service.delete_staff(session, staff_id, partner.id)
