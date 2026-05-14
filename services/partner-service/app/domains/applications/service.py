from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.accounts.service import get_account
from app.domains.applications.models import Application, ApplicationStatus
from app.domains.applications.schemas import ApplicationCreate, ApplicationUpdate
from app.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError


async def submit_application(
    session: AsyncSession, account_id: UUID, data: ApplicationCreate
) -> Application:
    await get_account(session, account_id)

    # Один аккаунт = одна активная заявка. Повторно можно подать, только если
    # предыдущая отклонена.
    result = await session.execute(
        select(Application).where(
            Application.account_id == account_id,
            Application.status.in_(
                [ApplicationStatus.PENDING, ApplicationStatus.APPROVED]
            ),
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise ConflictError(
            f"Account already has a {existing.status} application"
        )

    application = Application(
        account_id=account_id,
        business_name=data.business_name,
        inn=data.inn,
        category=data.category,
        contact_email=str(data.contact_email).lower(),
        contact_phone=data.contact_phone,
        description=data.description,
    )
    session.add(application)
    await session.commit()
    await session.refresh(application)
    return application


async def get_application(session: AsyncSession, application_id: UUID) -> Application:
    application = await session.get(Application, application_id)
    if application is None:
        raise NotFoundError("Application not found")
    return application


async def list_my_applications(
    session: AsyncSession, account_id: UUID
) -> list[Application]:
    result = await session.execute(
        select(Application)
        .where(Application.account_id == account_id)
        .order_by(Application.created_at.desc())
    )
    return list(result.scalars().all())


async def list_applications(
    session: AsyncSession,
    status_filter: ApplicationStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Application]:
    stmt = select(Application)
    if status_filter is not None:
        stmt = stmt.where(Application.status == status_filter)
    stmt = stmt.order_by(Application.created_at.asc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


def _decide(
    application: Application,
    target: ApplicationStatus,
    admin_id: UUID,
    comment: str | None,
) -> None:
    if application.status != ApplicationStatus.PENDING:
        raise BadRequestError(
            f"Application is already {application.status}, cannot change"
        )
    application.status = target
    application.decided_at = datetime.now(UTC)
    application.decided_by = admin_id
    application.decision_comment = comment


async def approve(
    session: AsyncSession,
    application_id: UUID,
    admin_id: UUID,
    comment: str | None = None,
) -> Application:
    application = await get_application(session, application_id)
    _decide(application, ApplicationStatus.APPROVED, admin_id, comment)
    # commit делает caller — он же создаёт Partner в той же транзакции.
    return application


async def reject(
    session: AsyncSession,
    application_id: UUID,
    admin_id: UUID,
    comment: str | None = None,
) -> Application:
    application = await get_application(session, application_id)
    _decide(application, ApplicationStatus.REJECTED, admin_id, comment)
    await session.commit()
    await session.refresh(application)
    return application


async def withdraw_my_pending(
    session: AsyncSession, account_id: UUID
) -> None:
    result = await session.execute(
        select(Application).where(
            Application.account_id == account_id,
            Application.status == ApplicationStatus.PENDING,
        )
    )
    for app in result.scalars().all():
        await session.delete(app)
    await session.commit()


async def update_my_pending(
    session: AsyncSession,
    account_id: UUID,
    application_id: UUID,
    data: ApplicationUpdate,
) -> Application:
    application = await get_application(session, application_id)
    if application.account_id != account_id:
        raise ForbiddenError("Application does not belong to this account")
    if application.status != ApplicationStatus.PENDING:
        raise BadRequestError(
            f"Application is {application.status}, cannot edit"
        )

    payload = data.model_dump(exclude_unset=True)
    if "contact_email" in payload and payload["contact_email"] is not None:
        payload["contact_email"] = str(payload["contact_email"]).lower()
    for key, value in payload.items():
        setattr(application, key, value)

    await session.commit()
    await session.refresh(application)
    return application
