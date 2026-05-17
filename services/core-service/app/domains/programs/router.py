from uuid import UUID

from fastapi import APIRouter, status

from app.deps import CurrentPartnerId, SessionDep
from app.domains.programs import service
from app.domains.programs.models import ProgramStatus
from app.domains.programs.schemas import (
    ProgramCreate,
    ProgramRead,
    ProgramUpdate,
    TierCreate,
    TierUpdate,
)

router = APIRouter(prefix="/programs", tags=["programs"])


@router.post("", response_model=ProgramRead, status_code=status.HTTP_201_CREATED)
async def create_program(
    data: ProgramCreate, partner_id: CurrentPartnerId, session: SessionDep
) -> ProgramRead:
    program = await service.create_program(session, partner_id, data)
    return ProgramRead.model_validate(program)


@router.get("", response_model=list[ProgramRead])
async def list_programs(
    partner_id: CurrentPartnerId, session: SessionDep
) -> list[ProgramRead]:
    programs = await service.list_programs_for_partner(session, partner_id)
    return [ProgramRead.model_validate(p) for p in programs]


@router.get("/{program_id}", response_model=ProgramRead)
async def get_program(
    program_id: UUID, partner_id: CurrentPartnerId, session: SessionDep
) -> ProgramRead:
    program = await service.get_program_for_partner(session, program_id, partner_id)
    return ProgramRead.model_validate(program)


@router.patch("/{program_id}", response_model=ProgramRead)
async def update_program(
    program_id: UUID,
    data: ProgramUpdate,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> ProgramRead:
    program = await service.update_program(session, program_id, partner_id, data)
    return ProgramRead.model_validate(program)


@router.post("/{program_id}/publish", response_model=ProgramRead)
async def publish_program(
    program_id: UUID, partner_id: CurrentPartnerId, session: SessionDep
) -> ProgramRead:
    program = await service.transition_status(
        session, program_id, partner_id, ProgramStatus.PUBLISHED
    )
    return ProgramRead.model_validate(program)


@router.post("/{program_id}/pause", response_model=ProgramRead)
async def pause_program(
    program_id: UUID, partner_id: CurrentPartnerId, session: SessionDep
) -> ProgramRead:
    program = await service.transition_status(
        session, program_id, partner_id, ProgramStatus.PAUSED
    )
    return ProgramRead.model_validate(program)


@router.post("/{program_id}/archive", response_model=ProgramRead)
async def archive_program(
    program_id: UUID, partner_id: CurrentPartnerId, session: SessionDep
) -> ProgramRead:
    program = await service.transition_status(
        session, program_id, partner_id, ProgramStatus.ARCHIVED
    )
    return ProgramRead.model_validate(program)


@router.post(
    "/{program_id}/tiers",
    response_model=ProgramRead,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить уровень лояльности",
)
async def add_tier(
    program_id: UUID,
    data: TierCreate,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> ProgramRead:
    """Добавляет уровень к программе. Имя и порог баллов уникальны в рамках программы.
    Нельзя добавлять уровни к архивированной программе."""
    program = await service.add_tier(session, program_id, partner_id, data)
    return ProgramRead.model_validate(program)


@router.patch(
    "/{program_id}/tiers/{tier_id}",
    response_model=ProgramRead,
    summary="Обновить уровень лояльности",
)
async def update_tier(
    program_id: UUID,
    tier_id: UUID,
    data: TierUpdate,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> ProgramRead:
    """Обновляет поля уровня. Все поля опциональны.
    Нельзя обновлять уровни архивированной программы."""
    program = await service.update_tier(session, program_id, tier_id, partner_id, data)
    return ProgramRead.model_validate(program)


@router.delete(
    "/{program_id}/tiers/{tier_id}",
    response_model=ProgramRead,
    status_code=status.HTTP_200_OK,
    summary="Удалить уровень лояльности",
)
async def delete_tier(
    program_id: UUID,
    tier_id: UUID,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> ProgramRead:
    """Удаляет уровень и возвращает обновлённую программу.
    Нельзя удалять уровни архивированной программы."""
    program = await service.delete_tier(session, program_id, tier_id, partner_id)
    return ProgramRead.model_validate(program)
