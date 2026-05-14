from uuid import UUID

from fastapi import APIRouter, status

from app.deps import CurrentPartnerId, SessionDep
from app.domains.rewards import service
from app.domains.rewards.schemas import RewardCreate, RewardRead, RewardUpdate

router = APIRouter(tags=["rewards"])


@router.post(
    "/programs/{program_id}/rewards",
    response_model=RewardRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_reward(
    program_id: UUID,
    data: RewardCreate,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> RewardRead:
    reward = await service.create_reward(session, partner_id, program_id, data)
    return RewardRead.model_validate(reward)


@router.get("/programs/{program_id}/rewards", response_model=list[RewardRead])
async def list_rewards(
    program_id: UUID,
    session: SessionDep,
    only_active: bool = False,
) -> list[RewardRead]:
    rewards = await service.list_rewards(session, program_id, only_active=only_active)
    return [RewardRead.model_validate(r) for r in rewards]


@router.get("/rewards/{reward_id}", response_model=RewardRead)
async def get_reward(reward_id: UUID, session: SessionDep) -> RewardRead:
    reward = await service.get_reward(session, reward_id)
    return RewardRead.model_validate(reward)


@router.patch("/rewards/{reward_id}", response_model=RewardRead)
async def update_reward(
    reward_id: UUID,
    data: RewardUpdate,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> RewardRead:
    reward = await service.update_reward(session, reward_id, partner_id, data)
    return RewardRead.model_validate(reward)


@router.delete("/rewards/{reward_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reward(
    reward_id: UUID, partner_id: CurrentPartnerId, session: SessionDep
) -> None:
    await service.delete_reward(session, reward_id, partner_id)
