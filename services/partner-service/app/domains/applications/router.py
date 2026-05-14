from uuid import UUID

from fastapi import APIRouter, Query, status

from app.deps import CurrentAccountId, CurrentAdminId, SessionDep
from app.domains.applications import service
from app.domains.applications.models import ApplicationStatus
from app.domains.applications.schemas import (
    ApplicationCreate,
    ApplicationDecision,
    ApplicationRead,
)
from app.domains.partners import service as partners_service
from app.domains.partners.schemas import PartnerRead

partner_router = APIRouter(prefix="/applications", tags=["applications"])
admin_router = APIRouter(prefix="/admin/applications", tags=["applications-admin"])


@partner_router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def submit_application(
    data: ApplicationCreate,
    account_id: CurrentAccountId,
    session: SessionDep,
) -> ApplicationRead:
    application = await service.submit_application(session, account_id, data)
    return ApplicationRead.model_validate(application)


@partner_router.get("/me", response_model=list[ApplicationRead])
async def list_my_applications(
    account_id: CurrentAccountId, session: SessionDep
) -> list[ApplicationRead]:
    applications = await service.list_my_applications(session, account_id)
    return [ApplicationRead.model_validate(a) for a in applications]


@admin_router.get("", response_model=list[ApplicationRead])
async def list_applications(
    session: SessionDep,
    _admin: CurrentAdminId,
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ApplicationRead]:
    applications = await service.list_applications(
        session, status_filter=status_filter, limit=limit, offset=offset
    )
    return [ApplicationRead.model_validate(a) for a in applications]


@admin_router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(
    application_id: UUID,
    session: SessionDep,
    _admin: CurrentAdminId,
) -> ApplicationRead:
    application = await service.get_application(session, application_id)
    return ApplicationRead.model_validate(application)


@admin_router.post("/{application_id}/approve", response_model=PartnerRead)
async def approve_application(
    application_id: UUID,
    data: ApplicationDecision,
    admin_id: CurrentAdminId,
    session: SessionDep,
) -> PartnerRead:
    partner = await partners_service.approve_application_and_create_partner(
        session, application_id, admin_id, data.comment
    )
    return PartnerRead.model_validate(partner)


@admin_router.post("/{application_id}/reject", response_model=ApplicationRead)
async def reject_application(
    application_id: UUID,
    data: ApplicationDecision,
    admin_id: CurrentAdminId,
    session: SessionDep,
) -> ApplicationRead:
    application = await service.reject(session, application_id, admin_id, data.comment)
    return ApplicationRead.model_validate(application)
