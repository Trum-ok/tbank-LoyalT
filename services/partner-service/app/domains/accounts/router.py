from fastapi import APIRouter, status
from loyalt_common import error_responses

from app.deps import CurrentAccountId, SessionDep
from app.domains.accounts import service
from app.domains.accounts.schemas import AccountCreate, AccountRead, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post(
    "",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация аккаунта предпринимателя",
    responses=error_responses(409),
)
async def signup(data: AccountCreate, session: SessionDep) -> AccountRead:
    """Создаёт аккаунт предпринимателя по email.

    С этого аккаунта подаётся заявка партнёра. 409 — аккаунт с таким email
    уже существует.
    """
    account = await service.create_account(session, data)
    return AccountRead.model_validate(account)


@router.get(
    "/me",
    response_model=AccountRead,
    summary="Мой аккаунт",
    responses=error_responses(404),
)
async def get_me(account_id: CurrentAccountId, session: SessionDep) -> AccountRead:
    """Профиль текущего аккаунта (по `X-Account-Id`). 404 — аккаунт не найден."""
    account = await service.get_account(session, account_id)
    return AccountRead.model_validate(account)


@router.patch(
    "/me",
    response_model=AccountRead,
    summary="Обновить мой аккаунт",
    responses=error_responses(404),
)
async def update_me(
    data: AccountUpdate, account_id: CurrentAccountId, session: SessionDep
) -> AccountRead:
    """Меняет имя/телефон текущего аккаунта. 404 — аккаунт не найден."""
    account = await service.update_account(session, account_id, data)
    return AccountRead.model_validate(account)
