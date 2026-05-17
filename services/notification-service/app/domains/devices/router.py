from uuid import UUID

from fastapi import APIRouter, status
from loyalt_common import error_responses

from app.deps import CurrentCustomerId, SessionDep
from app.domains.devices import service
from app.domains.devices.schemas import DeviceRead, DeviceRegister

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post(
    "",
    response_model=DeviceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Зарегистрировать push-устройство",
)
async def register_device(
    data: DeviceRegister, customer_id: CurrentCustomerId, session: SessionDep
) -> DeviceRead:
    """Регистрирует push-токен устройства клиента (приложение Т-Банка).

    Идемпотентно: повторная регистрация той же пары `(клиент, токен)`
    реактивирует устройство и обновляет платформу, новая запись не
    создаётся. На это устройство будут доставляться все уведомления
    клиента, пока оно активно.
    """
    device = await service.register_device(session, customer_id, data)
    return DeviceRead.model_validate(device)


@router.get(
    "",
    response_model=list[DeviceRead],
    summary="Мои активные устройства",
)
async def list_devices(
    customer_id: CurrentCustomerId, session: SessionDep
) -> list[DeviceRead]:
    """Список активных push-устройств клиента (новые сверху)."""
    devices = await service.list_devices(session, customer_id)
    return [DeviceRead.model_validate(d) for d in devices]


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отключить устройство",
    responses=error_responses(404),
)
async def deactivate_device(
    device_id: UUID, customer_id: CurrentCustomerId, session: SessionDep
) -> None:
    """Деактивирует устройство — уведомления на него больше не доставляются.

    404 — устройство не найдено или принадлежит другому клиенту.
    """
    await service.deactivate(session, customer_id, device_id)
