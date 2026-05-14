from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.devices.models import Device
from app.domains.devices.schemas import DeviceRegister
from app.errors import NotFoundError


async def register_device(
    session: AsyncSession, customer_id: UUID, data: DeviceRegister
) -> Device:
    # Идемпотентно: тот же (customer, token) — реактивируем и обновляем платформу.
    result = await session.execute(
        select(Device).where(
            Device.customer_id == customer_id, Device.token == data.token
        )
    )
    device = result.scalar_one_or_none()
    if device is not None:
        device.platform = data.platform
        device.is_active = True
        await session.commit()
        await session.refresh(device)
        return device

    device = Device(
        customer_id=customer_id,
        token=data.token,
        platform=data.platform,
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)
    return device


async def list_devices(session: AsyncSession, customer_id: UUID) -> list[Device]:
    result = await session.execute(
        select(Device)
        .where(Device.customer_id == customer_id, Device.is_active.is_(True))
        .order_by(Device.created_at.desc())
    )
    return list(result.scalars().all())


async def list_active_for_customer(
    session: AsyncSession, customer_id: UUID
) -> list[Device]:
    return await list_devices(session, customer_id)


async def deactivate(
    session: AsyncSession, customer_id: UUID, device_id: UUID
) -> None:
    device = await session.get(Device, device_id)
    if device is None or device.customer_id != customer_id:
        raise NotFoundError("Device not found")
    device.is_active = False
    await session.commit()
