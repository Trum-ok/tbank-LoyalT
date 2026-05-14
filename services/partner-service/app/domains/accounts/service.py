from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.accounts.models import Account
from app.domains.accounts.schemas import AccountCreate, AccountUpdate
from app.errors import ConflictError, NotFoundError


async def create_account(session: AsyncSession, data: AccountCreate) -> Account:
    account = Account(
        email=str(data.email).lower(),
        full_name=data.full_name,
        phone=data.phone,
    )
    session.add(account)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Account with this email already exists") from exc
    await session.refresh(account)
    return account


async def get_account(session: AsyncSession, account_id: UUID) -> Account:
    account = await session.get(Account, account_id)
    if account is None:
        raise NotFoundError("Account not found")
    return account


async def update_account(
    session: AsyncSession, account_id: UUID, data: AccountUpdate
) -> Account:
    account = await get_account(session, account_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    await session.commit()
    await session.refresh(account)
    return account
