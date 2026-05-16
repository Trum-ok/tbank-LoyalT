"""Логика рассылок партнёра.

Хранение черновиков/истории — здесь (partner-service). Аудитория резолвится
синхронно в core-service, фан-аут уведомлений — асинхронно через Kafka
(событие `partner.broadcast`, notification-service создаёт по уведомлению
на каждого клиента).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import core as core_client
from app.domains.broadcasts.models import Broadcast, BroadcastStatus
from app.domains.broadcasts.schemas import BroadcastCreate, BroadcastUpdate
from app.errors import BadRequestError, ForbiddenError, NotFoundError
from app.events import publisher


async def list_broadcasts(
    session: AsyncSession, partner_id: UUID
) -> list[Broadcast]:
    stmt = (
        select(Broadcast)
        .where(Broadcast.partner_id == partner_id)
        .order_by(Broadcast.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_broadcast(
    session: AsyncSession, partner_id: UUID, broadcast_id: UUID
) -> Broadcast:
    broadcast = await session.get(Broadcast, broadcast_id)
    if broadcast is None:
        raise NotFoundError("Broadcast not found")
    if broadcast.partner_id != partner_id:
        raise ForbiddenError("Broadcast belongs to another partner")
    return broadcast


async def create_draft(
    session: AsyncSession, partner_id: UUID, data: BroadcastCreate
) -> Broadcast:
    broadcast = Broadcast(
        partner_id=partner_id,
        title=data.title,
        body=data.body,
        segment=data.segment,
        program_id=data.program_id,
        status=BroadcastStatus.DRAFT,
    )
    session.add(broadcast)
    await session.commit()
    await session.refresh(broadcast)
    return broadcast


async def update_draft(
    session: AsyncSession,
    partner_id: UUID,
    broadcast_id: UUID,
    data: BroadcastUpdate,
) -> Broadcast:
    broadcast = await get_broadcast(session, partner_id, broadcast_id)
    if broadcast.status != BroadcastStatus.DRAFT:
        raise BadRequestError("Можно редактировать только черновик")
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(broadcast, field, value)
    await session.commit()
    await session.refresh(broadcast)
    return broadcast


async def delete_draft(
    session: AsyncSession, partner_id: UUID, broadcast_id: UUID
) -> None:
    broadcast = await get_broadcast(session, partner_id, broadcast_id)
    if broadcast.status != BroadcastStatus.DRAFT:
        raise BadRequestError("Можно удалить только черновик")
    await session.delete(broadcast)
    await session.commit()


async def audience_count(
    partner_id: UUID,
    segment: str,
    program_id: UUID | None = None,
) -> int:
    ids = await core_client.resolve_audience(partner_id, segment, program_id)
    return len(ids)


async def send_broadcast(
    session: AsyncSession, partner_id: UUID, broadcast_id: UUID
) -> Broadcast:
    broadcast = await get_broadcast(session, partner_id, broadcast_id)
    if broadcast.status == BroadcastStatus.SENT:
        raise BadRequestError("Рассылка уже отправлена")

    customer_ids = await core_client.resolve_audience(
        partner_id, broadcast.segment, broadcast.program_id
    )

    broadcast.audience_count = len(customer_ids)
    broadcast.sent_count = len(customer_ids)
    broadcast.status = BroadcastStatus.SENT
    broadcast.sent_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(broadcast)

    # Асинхронный фан-аут: notification-service создаст по уведомлению на
    # каждого клиента из customer_ids.
    await publisher.publish(
        "partner.broadcast",
        {
            "broadcast_id": broadcast.id,
            "partner_id": partner_id,
            "title": broadcast.title,
            "body": broadcast.body,
            "segment": broadcast.segment,
            "customer_ids": customer_ids,
        },
        key=str(broadcast.id),
    )
    return broadcast
