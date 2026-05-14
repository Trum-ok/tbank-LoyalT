from uuid import UUID

from fastapi import APIRouter, status

from app.deps import CurrentCustomerId, SessionDep
from app.domains.enrollments import service
from app.domains.enrollments.schemas import (
    EnrollmentCreate,
    EnrollmentRead,
    EnrollmentUpdate,
)

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.post("", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED)
async def enroll(
    data: EnrollmentCreate,
    customer_id: CurrentCustomerId,
    session: SessionDep,
) -> EnrollmentRead:
    enrollment = await service.enroll(session, customer_id, data)
    return EnrollmentRead.model_validate(enrollment)


@router.get("", response_model=list[EnrollmentRead])
async def list_enrollments(
    customer_id: CurrentCustomerId,
    session: SessionDep,
    include_archived: bool = False,
) -> list[EnrollmentRead]:
    enrollments = await service.list_enrollments(
        session, customer_id, include_archived=include_archived
    )
    return [EnrollmentRead.model_validate(e) for e in enrollments]


@router.get("/{enrollment_id}", response_model=EnrollmentRead)
async def get_enrollment(
    enrollment_id: UUID, customer_id: CurrentCustomerId, session: SessionDep
) -> EnrollmentRead:
    enrollment = await service.get_enrollment_for_customer(
        session, enrollment_id, customer_id
    )
    return EnrollmentRead.model_validate(enrollment)


@router.patch("/{enrollment_id}", response_model=EnrollmentRead)
async def update_enrollment(
    enrollment_id: UUID,
    data: EnrollmentUpdate,
    customer_id: CurrentCustomerId,
    session: SessionDep,
) -> EnrollmentRead:
    enrollment = await service.update_enrollment(
        session, enrollment_id, customer_id, data
    )
    return EnrollmentRead.model_validate(enrollment)


@router.delete("/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_enrollment(
    enrollment_id: UUID, customer_id: CurrentCustomerId, session: SessionDep
) -> None:
    await service.delete_enrollment(session, enrollment_id, customer_id)
