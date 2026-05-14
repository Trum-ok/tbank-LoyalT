from fastapi import APIRouter, status

from app.deps import CurrentAccountId, SessionDep
from app.domains.accounts import service
from app.domains.accounts.schemas import AccountCreate, AccountRead, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def signup(data: AccountCreate, session: SessionDep) -> AccountRead:
    account = await service.create_account(session, data)
    return AccountRead.model_validate(account)


@router.get("/me", response_model=AccountRead)
async def get_me(account_id: CurrentAccountId, session: SessionDep) -> AccountRead:
    account = await service.get_account(session, account_id)
    return AccountRead.model_validate(account)


@router.patch("/me", response_model=AccountRead)
async def update_me(
    data: AccountUpdate, account_id: CurrentAccountId, session: SessionDep
) -> AccountRead:
    account = await service.update_account(session, account_id, data)
    return AccountRead.model_validate(account)
