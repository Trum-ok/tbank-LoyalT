from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.transactions.models import Transaction, TransactionType
from app.errors import ForbiddenError, NotFoundError


async def get_transaction(session: AsyncSession, transaction_id: UUID) -> Transaction:
    # PK составной (id, partner_id) из-за партиционирования, но id глобально
    # уникален (uuid4) — ищем по одному id.
    result = await session.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if transaction is None:
        raise NotFoundError("Transaction not found")
    return transaction


async def list_for_customer(
    session: AsyncSession,
    customer_id: UUID,
    program_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Transaction]:
    # Клиенту не показываем «кухню» отмен: ни сами reversal-операции,
    # ни исходную транзакцию, которую откатили (баланс при этом сходится —
    # начисление+отмена в сумме дают ноль и просто исчезают из истории).
    stmt = select(Transaction).where(
        Transaction.customer_id == customer_id,
        Transaction.type != TransactionType.REVERSAL,
        Transaction.is_reversed.is_(False),
    )
    if program_id is not None:
        stmt = stmt.where(Transaction.program_id == program_id)
    stmt = stmt.order_by(Transaction.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_for_partner(
    session: AsyncSession,
    partner_id: UUID,
    program_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Transaction]:
    stmt = select(Transaction).where(Transaction.partner_id == partner_id)
    if program_id is not None:
        stmt = stmt.where(Transaction.program_id == program_id)
    stmt = stmt.order_by(Transaction.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_for_customer(
    session: AsyncSession, transaction_id: UUID, customer_id: UUID
) -> Transaction:
    transaction = await get_transaction(session, transaction_id)
    if transaction.customer_id != customer_id:
        raise ForbiddenError("Transaction belongs to another customer")
    return transaction


async def get_for_partner(
    session: AsyncSession, transaction_id: UUID, partner_id: UUID
) -> Transaction:
    transaction = await get_transaction(session, transaction_id)
    if transaction.partner_id != partner_id:
        raise ForbiddenError("Transaction belongs to another partner")
    return transaction
