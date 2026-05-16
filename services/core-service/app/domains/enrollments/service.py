from uuid import UUID

from sqlalchemy import BigInteger, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.enrollments.models import Customer, Enrollment
from app.domains.enrollments.schemas import EnrollmentCreate, EnrollmentUpdate
from app.domains.programs.models import ProgramStatus
from app.domains.programs.service import get_program
from app.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError


async def ensure_customer(session: AsyncSession, customer_id: UUID) -> Customer:
    customer = await session.get(Customer, customer_id)
    if customer is not None:
        return customer
    customer = Customer(id=customer_id)
    session.add(customer)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        customer = await session.get(Customer, customer_id)
        if customer is None:
            raise
    return customer


async def generate_short_code(session: AsyncSession) -> str:
    """Цифровой код подключения для диктовки на кассе.

    Последовательный, от 4 до 9 цифр (1000, 1001, … 999999999) —
    короткий, пока подключений немного.
    """
    result = await session.execute(
        select(func.max(cast(Enrollment.short_code, BigInteger)))
    )
    current = result.scalar() or 0
    nxt = max(current + 1, 1000)
    if nxt > 999_999_999:
        raise ConflictError("Failed to allocate a unique enrollment code")
    return str(nxt)


async def enroll(
    session: AsyncSession, customer_id: UUID, data: EnrollmentCreate
) -> Enrollment:
    program = await get_program(session, data.program_id)
    if program.status != ProgramStatus.PUBLISHED:
        raise BadRequestError("Program is not available for enrollment")

    await ensure_customer(session, customer_id)
    enrollment = Enrollment(
        customer_id=customer_id,
        program_id=data.program_id,
        display_name=data.display_name,
        short_code=await generate_short_code(session),
    )
    session.add(enrollment)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Customer is already enrolled in this program") from exc
    await session.refresh(enrollment)
    return enrollment


async def get_enrollment(session: AsyncSession, enrollment_id: UUID) -> Enrollment:
    enrollment = await session.get(Enrollment, enrollment_id)
    if enrollment is None:
        raise NotFoundError("Enrollment not found")
    return enrollment


async def get_enrollment_for_customer(
    session: AsyncSession, enrollment_id: UUID, customer_id: UUID
) -> Enrollment:
    enrollment = await get_enrollment(session, enrollment_id)
    if enrollment.customer_id != customer_id:
        raise ForbiddenError("Enrollment belongs to another customer")
    return enrollment


async def get_enrollment_by_pair(
    session: AsyncSession, customer_id: UUID, program_id: UUID
) -> Enrollment:
    result = await session.execute(
        select(Enrollment).where(
            Enrollment.customer_id == customer_id,
            Enrollment.program_id == program_id,
        )
    )
    enrollment = result.scalar_one_or_none()
    if enrollment is None:
        raise NotFoundError("Customer is not enrolled in this program")
    return enrollment


async def list_enrollments(
    session: AsyncSession, customer_id: UUID, include_archived: bool = False
) -> list[Enrollment]:
    stmt = select(Enrollment).where(Enrollment.customer_id == customer_id)
    if not include_archived:
        stmt = stmt.where(Enrollment.is_archived.is_(False))
    stmt = stmt.order_by(Enrollment.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_enrollment(
    session: AsyncSession,
    enrollment_id: UUID,
    customer_id: UUID,
    data: EnrollmentUpdate,
) -> Enrollment:
    enrollment = await get_enrollment_for_customer(session, enrollment_id, customer_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(enrollment, field, value)
    await session.commit()
    await session.refresh(enrollment)
    return enrollment


async def delete_enrollment(
    session: AsyncSession, enrollment_id: UUID, customer_id: UUID
) -> None:
    enrollment = await get_enrollment_for_customer(session, enrollment_id, customer_id)
    await session.delete(enrollment)
    await session.commit()
