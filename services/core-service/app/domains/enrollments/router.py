from uuid import UUID

from fastapi import APIRouter, status
from loyalt_common import error_responses

from app.deps import CurrentCustomerId, SessionDep
from app.domains.enrollments import service
from app.domains.enrollments.schemas import (
    EnrollmentCreate,
    EnrollmentRead,
    EnrollmentUpdate,
)

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.post(
    "",
    response_model=EnrollmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Подключиться к программе",
    responses=error_responses(400, 409),
)
async def enroll(
    data: EnrollmentCreate,
    customer_id: CurrentCustomerId,
    session: SessionDep,
) -> EnrollmentRead:
    """Подключает клиента к программе лояльности и выдаёт короткий код/QR.

    400 — программа недоступна для подключения; 409 — клиент уже подключён.
    """
    enrollment = await service.enroll(session, customer_id, data)
    return EnrollmentRead.model_validate(enrollment)


@router.get(
    "",
    response_model=list[EnrollmentRead],
    summary="Мои подключения",
)
async def list_enrollments(
    customer_id: CurrentCustomerId,
    session: SessionDep,
    include_archived: bool = False,
) -> list[EnrollmentRead]:
    """Список подключений клиента; `include_archived` — с архивными."""
    enrollments = await service.list_enrollments(
        session, customer_id, include_archived=include_archived
    )
    return [EnrollmentRead.model_validate(e) for e in enrollments]


@router.get(
    "/{enrollment_id}",
    response_model=EnrollmentRead,
    summary="Подключение по id",
    responses=error_responses(403, 404),
)
async def get_enrollment(
    enrollment_id: UUID, customer_id: CurrentCustomerId, session: SessionDep
) -> EnrollmentRead:
    """Одно подключение клиента. 404 — не найдено, 403 — чужое."""
    enrollment = await service.get_enrollment_for_customer(
        session, enrollment_id, customer_id
    )
    return EnrollmentRead.model_validate(enrollment)


@router.patch(
    "/{enrollment_id}",
    response_model=EnrollmentRead,
    summary="Изменить подключение",
    responses=error_responses(403, 404),
)
async def update_enrollment(
    enrollment_id: UUID,
    data: EnrollmentUpdate,
    customer_id: CurrentCustomerId,
    session: SessionDep,
) -> EnrollmentRead:
    """Частичное обновление подключения. 404 — не найдено, 403 — чужое."""
    enrollment = await service.update_enrollment(
        session, enrollment_id, customer_id, data
    )
    return EnrollmentRead.model_validate(enrollment)


@router.delete(
    "/{enrollment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отключиться от программы",
    responses=error_responses(403, 404),
)
async def delete_enrollment(
    enrollment_id: UUID, customer_id: CurrentCustomerId, session: SessionDep
) -> None:
    """Архивирует подключение клиента. 404 — не найдено, 403 — чужое."""
    await service.delete_enrollment(session, enrollment_id, customer_id)
