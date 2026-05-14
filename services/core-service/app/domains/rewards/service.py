from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.programs.service import get_program, get_program_for_partner
from app.domains.rewards.models import Reward
from app.domains.rewards.schemas import RewardCreate, RewardUpdate
from app.errors import ForbiddenError, NotFoundError


async def create_reward(
    session: AsyncSession, partner_id: UUID, program_id: UUID, data: RewardCreate
) -> Reward:
    await get_program_for_partner(session, program_id, partner_id)
    reward = Reward(program_id=program_id, **data.model_dump())
    session.add(reward)
    await session.commit()
    await session.refresh(reward)
    return reward


async def get_reward(session: AsyncSession, reward_id: UUID) -> Reward:
    reward = await session.get(Reward, reward_id)
    if reward is None:
        raise NotFoundError("Reward not found")
    return reward


async def get_reward_for_partner(
    session: AsyncSession, reward_id: UUID, partner_id: UUID
) -> Reward:
    reward = await get_reward(session, reward_id)
    program = await get_program(session, reward.program_id)
    if program.partner_id != partner_id:
        raise ForbiddenError("Reward belongs to another partner")
    return reward


async def list_rewards(
    session: AsyncSession, program_id: UUID, only_active: bool = False
) -> list[Reward]:
    stmt = select(Reward).where(Reward.program_id == program_id)
    if only_active:
        stmt = stmt.where(Reward.is_active.is_(True))
    stmt = stmt.order_by(Reward.cost_points.asc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_reward(
    session: AsyncSession, reward_id: UUID, partner_id: UUID, data: RewardUpdate
) -> Reward:
    reward = await get_reward_for_partner(session, reward_id, partner_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(reward, field, value)
    await session.commit()
    await session.refresh(reward)
    return reward


async def delete_reward(
    session: AsyncSession, reward_id: UUID, partner_id: UUID
) -> None:
    reward = await get_reward_for_partner(session, reward_id, partner_id)
    await session.delete(reward)
    await session.commit()
