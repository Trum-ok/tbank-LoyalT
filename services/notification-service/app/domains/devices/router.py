from uuid import UUID

from fastapi import APIRouter, status

from app.deps import CurrentCustomerId, SessionDep
from app.domains.devices import service
from app.domains.devices.schemas import DeviceRead, DeviceRegister

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
async def register_device(
    data: DeviceRegister, customer_id: CurrentCustomerId, session: SessionDep
) -> DeviceRead:
    device = await service.register_device(session, customer_id, data)
    return DeviceRead.model_validate(device)


@router.get("", response_model=list[DeviceRead])
async def list_devices(
    customer_id: CurrentCustomerId, session: SessionDep
) -> list[DeviceRead]:
    devices = await service.list_devices(session, customer_id)
    return [DeviceRead.model_validate(d) for d in devices]


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_device(
    device_id: UUID, customer_id: CurrentCustomerId, session: SessionDep
) -> None:
    await service.deactivate(session, customer_id, device_id)
