from uuid import UUID

from fastapi import APIRouter, status

from app.deps import CurrentCustomerId, CurrentPartnerId, SessionDep
from app.domains.points import service
from app.domains.points.schemas import (
    AccrueRequest,
    BalanceRead,
    EnrollmentLookup,
    PointsOperationResult,
    RedeemRequest,
    ReverseRequest,
    RewardOption,
)
from app.domains.programs.schemas import TierRead
from app.domains.programs.service import get_current_tier
from app.domains.transactions.schemas import TransactionRead

partner_router = APIRouter(prefix="/points", tags=["points"])
customer_router = APIRouter(prefix="/balance", tags=["balance"])


@partner_router.post(
    "/accrue",
    response_model=PointsOperationResult,
    status_code=status.HTTP_201_CREATED,
)
async def accrue(
    req: AccrueRequest, partner_id: CurrentPartnerId, session: SessionDep
) -> PointsOperationResult:
    transaction, balance, tier = await service.accrue(session, partner_id, req)
    return PointsOperationResult(
        transaction=TransactionRead.model_validate(transaction),
        balance_after=balance,
        current_tier=TierRead.model_validate(tier) if tier is not None else None,
    )


def _build_lookup(enrollment, program, rewards) -> EnrollmentLookup:
    tier = get_current_tier(enrollment.points_balance, program.tiers)
    return EnrollmentLookup(
        enrollment_id=enrollment.id,
        customer_id=enrollment.customer_id,
        program_id=program.id,
        short_code=enrollment.short_code,
        program_name=program.name,
        program_type=program.type,
        program_status=program.status,
        accrual_rule=program.accrual_rule or {},
        min_redemption=program.min_redemption,
        points_balance=enrollment.points_balance,
        rewards=[
            RewardOption(
                id=r.id,
                title=r.title,
                description=r.description,
                cost_points=r.cost_points,
                type=r.type,
            )
            for r in rewards
        ],
        current_tier=TierRead.model_validate(tier) if tier is not None else None,
    )


@partner_router.get("/lookup/{enrollment_id}", response_model=EnrollmentLookup)
async def lookup(
    enrollment_id: UUID, partner_id: CurrentPartnerId, session: SessionDep
) -> EnrollmentLookup:
    enrollment, program, rewards = await service.lookup_enrollment(
        session, partner_id, enrollment_id
    )
    return _build_lookup(enrollment, program, rewards)


@partner_router.get("/lookup-code/{code}", response_model=EnrollmentLookup)
async def lookup_by_code(
    code: str, partner_id: CurrentPartnerId, session: SessionDep
) -> EnrollmentLookup:
    enrollment, program, rewards = await service.lookup_by_short_code(
        session, partner_id, code
    )
    return _build_lookup(enrollment, program, rewards)


@partner_router.post(
    "/redeem",
    response_model=PointsOperationResult,
    status_code=status.HTTP_201_CREATED,
)
async def redeem(
    req: RedeemRequest, partner_id: CurrentPartnerId, session: SessionDep
) -> PointsOperationResult:
    transaction, balance, tier = await service.redeem(session, partner_id, req)
    return PointsOperationResult(
        transaction=TransactionRead.model_validate(transaction),
        balance_after=balance,
        current_tier=TierRead.model_validate(tier) if tier is not None else None,
    )


@partner_router.post(
    "/transactions/{transaction_id}/reverse",
    response_model=PointsOperationResult,
    status_code=status.HTTP_201_CREATED,
)
async def reverse(
    transaction_id: UUID,
    req: ReverseRequest,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> PointsOperationResult:
    transaction, balance, tier = await service.reverse(
        session, partner_id, transaction_id, req.description
    )
    return PointsOperationResult(
        transaction=TransactionRead.model_validate(transaction),
        balance_after=balance,
        current_tier=TierRead.model_validate(tier) if tier is not None else None,
    )


@customer_router.get("", response_model=list[BalanceRead])
async def list_my_balances(
    customer_id: CurrentCustomerId, session: SessionDep
) -> list[BalanceRead]:
    enrollments = await service.list_balances(session, customer_id)
    return [
        BalanceRead(
            enrollment_id=e.id,
            customer_id=e.customer_id,
            program_id=e.program_id,
            points_balance=e.points_balance,
            updated_at=e.updated_at,
        )
        for e in enrollments
    ]


@customer_router.get("/{program_id}", response_model=BalanceRead)
async def get_my_balance(
    program_id: UUID, customer_id: CurrentCustomerId, session: SessionDep
) -> BalanceRead:
    enrollment = await service.get_balance(session, customer_id, program_id)
    return BalanceRead(
        enrollment_id=enrollment.id,
        customer_id=enrollment.customer_id,
        program_id=enrollment.program_id,
        points_balance=enrollment.points_balance,
        updated_at=enrollment.updated_at,
    )
