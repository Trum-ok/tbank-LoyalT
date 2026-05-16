from uuid import UUID

from fastapi import APIRouter, status

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


@auth_router.post("/login", response_model=StaffLoginResponse)
async def login(data: StaffLoginRequest, session: SessionDep) -> StaffLoginResponse:
    staff, partner = await service.authenticate(session, data.login_code, data.pin)
    return StaffLoginResponse(
        access_token=tokens.issue(staff.id, partner.id),
        token_type="bearer",
        staff_id=staff.id,
        staff_name=staff.name,
        partner_id=partner.id,
        partner_name=partner.name,
    )


@auth_router.get("/me", response_model=StaffRead)
async def get_me(staff_id: CurrentStaffId, session: SessionDep) -> StaffRead:
    staff = await service.get_staff(session, staff_id)
    return StaffRead.model_validate(staff)


@router.get("", response_model=list[StaffRead])
async def list_staff(
    account_id: CurrentAccountId, session: SessionDep
) -> list[StaffRead]:
    partner = await get_partner_by_account(session, account_id)
    rows = await service.list_staff(session, partner.id)
    return [StaffRead.model_validate(s) for s in rows]


@router.post("", response_model=StaffRead, status_code=status.HTTP_201_CREATED)
async def create_staff(
    data: StaffCreate, account_id: CurrentAccountId, session: SessionDep
) -> StaffRead:
    partner = await get_partner_by_account(session, account_id)
    staff = await service.create_staff(session, partner.id, data)
    return StaffRead.model_validate(staff)


@router.patch("/{staff_id}", response_model=StaffRead)
async def update_staff(
    staff_id: UUID,
    data: StaffUpdate,
    account_id: CurrentAccountId,
    session: SessionDep,
) -> StaffRead:
    partner = await get_partner_by_account(session, account_id)
    staff = await service.update_staff(session, staff_id, partner.id, data)
    return StaffRead.model_validate(staff)


@router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_staff(
    staff_id: UUID, account_id: CurrentAccountId, session: SessionDep
) -> None:
    partner = await get_partner_by_account(session, account_id)
    await service.delete_staff(session, staff_id, partner.id)
