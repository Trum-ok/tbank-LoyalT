from uuid import UUID

from sqlalchemy import exists, func, literal_column, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog.schemas import (
    CatalogCategory,
    CatalogProgram,
    CatalogProgramDetail,
)
from app.domains.partners.models import (
    Partner,
    PartnerCategory,
    PartnerCategory_,
    PartnerStatus,
)
from app.domains.programs.models import Program, ProgramStatus, ProgramTier
from app.domains.programs.schemas import TierRead
from app.domains.rewards.schemas import RewardRead
from app.domains.rewards.service import list_rewards

_CATEGORY_LABELS: dict[PartnerCategory, str] = {
    PartnerCategory.FOOD: "Еда и напитки",
    PartnerCategory.BEAUTY: "Красота и здоровье",
    PartnerCategory.RETAIL: "Розница",
    PartnerCategory.SERVICES: "Услуги",
    PartnerCategory.ENTERTAINMENT: "Развлечения",
}


# Категории партнёра одним массивом через коррелированный подзапрос —
# чтобы не плодить строки JOIN'ом и сохранить колоночный select.
_CATEGORIES_SUBQ = (
    select(
        func.coalesce(
            func.array_agg(
                aggregate_order_by(PartnerCategory_.category, PartnerCategory_.category)
            ),
            literal_column("ARRAY[]::varchar[]"),
        )
    )
    .where(PartnerCategory_.partner_id == Partner.id)
    .correlate(Partner)
    .scalar_subquery()
)

_BASE_COLUMNS = (
    Program.id.label("program_id"),
    Partner.id.label("partner_id"),
    Partner.name.label("partner_name"),
    Partner.logo_url.label("partner_logo_url"),
    Partner.brand_color.label("partner_brand_color"),
    _CATEGORIES_SUBQ.label("categories"),
    Program.name.label("program_name"),
    Program.description.label("description"),
    Program.type.label("type"),
)

_DETAIL_COLUMNS = (
    *_BASE_COLUMNS,
    Program.accrual_rule.label("accrual_rule"),
    Program.points_ttl_days.label("points_ttl_days"),
    Program.min_redemption.label("min_redemption"),
)


def _base_query():
    return (
        select(*_BASE_COLUMNS)
        .join(Partner, Partner.id == Program.partner_id)
        .where(
            Program.status == ProgramStatus.PUBLISHED,
            Partner.status == PartnerStatus.ACTIVE,
        )
    )


async def get_catalog_program(
    session: AsyncSession, program_id: UUID
) -> CatalogProgramDetail | None:
    stmt = (
        select(*_DETAIL_COLUMNS)
        .join(Partner, Partner.id == Program.partner_id)
        .where(
            Program.id == program_id,
            Program.status == ProgramStatus.PUBLISHED,
            Partner.status == PartnerStatus.ACTIVE,
        )
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        return None
    detail = CatalogProgramDetail.model_validate(row, from_attributes=True)

    # Тиры — отдельным запросом (программа/партнёр уже получены выше одним
    # JOIN'ом, повторно тянуть их через get_program не нужно).
    tiers = (
        await session.execute(
            select(ProgramTier)
            .where(ProgramTier.program_id == program_id)
            .order_by(ProgramTier.threshold_points)
        )
    ).scalars()
    detail.tiers = [TierRead.model_validate(t) for t in tiers]

    rewards = await list_rewards(session, program_id, only_active=True)
    detail.rewards = [RewardRead.model_validate(r) for r in rewards]

    return detail


async def search_catalog(
    session: AsyncSession,
    category: PartnerCategory | None = None,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[CatalogProgram]:
    stmt = _base_query()
    if category is not None:
        stmt = stmt.where(
            exists().where(
                PartnerCategory_.partner_id == Partner.id,
                PartnerCategory_.category == category.value,
            )
        )
    if query:
        stmt = stmt.where(
            func.lower(Partner.name).contains(query.lower(), autoescape=True)
        )
    stmt = stmt.order_by(Partner.name.asc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return [CatalogProgram.model_validate(row, from_attributes=True) for row in result]


async def list_categories(session: AsyncSession) -> list[CatalogCategory]:
    stmt = (
        select(PartnerCategory_.category, func.count(Program.id))
        .select_from(PartnerCategory_)
        .join(Partner, Partner.id == PartnerCategory_.partner_id)
        .join(Program, Program.partner_id == Partner.id)
        .where(
            Program.status == ProgramStatus.PUBLISHED,
            Partner.status == PartnerStatus.ACTIVE,
        )
        .group_by(PartnerCategory_.category)
    )
    result = await session.execute(stmt)
    counts: dict[str, int] = {row[0]: row[1] for row in result.all()}
    return [
        CatalogCategory(code=cat, label=label, programs_count=counts.get(cat.value, 0))
        for cat, label in _CATEGORY_LABELS.items()
    ]
