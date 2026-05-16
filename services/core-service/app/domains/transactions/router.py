from uuid import UUID

from fastapi import APIRouter, Query
from loyalt_common import error_responses

from app.deps import (
    CurrentCustomerId,
    CurrentPartnerId,
    ReadSessionDep,
    SessionDep,
)
from app.domains.transactions import service
from app.domains.transactions.schemas import TransactionRead

customer_router = APIRouter(prefix="/transactions", tags=["transactions"])
partner_router = APIRouter(prefix="/partner/transactions", tags=["transactions"])


@customer_router.get(
    "",
    response_model=list[TransactionRead],
    summary="Моя история операций",
)
async def list_my_transactions(
    customer_id: CurrentCustomerId,
    session: ReadSessionDep,
    program_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[TransactionRead]:
    txs = await service.list_for_customer(
        session, customer_id, program_id=program_id, limit=limit, offset=offset
    )
    """История операций клиента; фильтр по `program_id`, пагинация."""
    return [TransactionRead.model_validate(t) for t in txs]


@customer_router.get(
    "/{transaction_id}",
    response_model=TransactionRead,
    summary="Моя операция по id",
    responses=error_responses(403, 404),
)
async def get_my_transaction(
    transaction_id: UUID, customer_id: CurrentCustomerId, session: SessionDep
) -> TransactionRead:
    """Одна операция клиента. 404 — не найдена, 403 — чужая."""
    transaction = await service.get_for_customer(session, transaction_id, customer_id)
    return TransactionRead.model_validate(transaction)


@partner_router.get(
    "",
    response_model=list[TransactionRead],
    summary="История операций партнёра",
)
async def list_partner_transactions(
    partner_id: CurrentPartnerId,
    session: ReadSessionDep,
    program_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[TransactionRead]:
    """История операций по программам партнёра; фильтр и пагинация."""
    txs = await service.list_for_partner(
        session, partner_id, program_id=program_id, limit=limit, offset=offset
    )
    return [TransactionRead.model_validate(t) for t in txs]
