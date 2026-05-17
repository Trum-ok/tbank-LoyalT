from uuid import UUID

from fastapi import APIRouter, status

from app.deps import CurrentPartnerId, SessionDep
from app.domains.programs import service, trigger_service
from app.domains.programs.models import ProgramStatus
from app.domains.programs.schemas import (
    ProgramCreate,
    ProgramRead,
    ProgramUpdate,
    TierCreate,
    TierUpdate,
)
from app.domains.programs.trigger_schemas import (
    BonusTriggerCreate,
    BonusTriggerRead,
    BonusTriggerUpdate,
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


# ── Бонусные кампании ────────────────────────────────────────────────────────


@router.get(
    "/{program_id}/triggers",
    response_model=list[BonusTriggerRead],
    summary="Список бонусных кампаний программы",
)
async def list_triggers(
    program_id: UUID,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> list[BonusTriggerRead]:
    triggers = await trigger_service.list_triggers(session, program_id)
    return [BonusTriggerRead.model_validate(t) for t in triggers]


@router.post(
    "/{program_id}/triggers",
    response_model=BonusTriggerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать бонусную кампанию",
)
async def create_trigger(
    program_id: UUID,
    data: BonusTriggerCreate,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> BonusTriggerRead:
    trigger = await trigger_service.create_trigger(
        session, program_id, partner_id, data
    )
    return BonusTriggerRead.model_validate(trigger)


@router.patch(
    "/{program_id}/triggers/{trigger_id}",
    response_model=BonusTriggerRead,
    summary="Обновить бонусную кампанию",
)
async def update_trigger(
    program_id: UUID,
    trigger_id: UUID,
    data: BonusTriggerUpdate,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> BonusTriggerRead:
    trigger = await trigger_service.update_trigger(
        session, program_id, trigger_id, partner_id, data
    )
    return BonusTriggerRead.model_validate(trigger)


@router.delete(
    "/{program_id}/triggers/{trigger_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить бонусную кампанию",
)
async def delete_trigger(
    program_id: UUID,
    trigger_id: UUID,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> None:
    await trigger_service.delete_trigger(session, program_id, trigger_id, partner_id)


@router.post(
    "/{program_id}/triggers/{trigger_id}/fire",
    summary="Запустить MANUAL-кампанию вручную",
)
async def fire_trigger(
    program_id: UUID,
    trigger_id: UUID,
    partner_id: CurrentPartnerId,
    session: SessionDep,
) -> dict[str, int]:
    fired_count = await trigger_service.fire_trigger(
        session, trigger_id, program_id, partner_id
    )
    return {"fired_count": fired_count}
