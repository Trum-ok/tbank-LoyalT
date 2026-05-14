from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog.schemas import CatalogCategory, CatalogProgram
from app.domains.partners.models import Partner, PartnerCategory, PartnerStatus
from app.domains.programs.models import Program, ProgramStatus

_CATEGORY_LABELS: dict[PartnerCategory, str] = {
    PartnerCategory.FOOD: "Еда и напитки",
    PartnerCategory.BEAUTY: "Красота и здоровье",
    PartnerCategory.RETAIL: "Розница",
    PartnerCategory.SERVICES: "Услуги",
    PartnerCategory.ENTERTAINMENT: "Развлечения",
}


def _base_query():
    return (
        select(
            Program.id.label("program_id"),
            Partner.id.label("partner_id"),
            Partner.name.label("partner_name"),
            Partner.logo_url.label("partner_logo_url"),
            Partner.brand_color.label("partner_brand_color"),
            Partner.category.label("category"),
            Program.name.label("program_name"),
            Program.description.label("description"),
            Program.type.label("type"),
        )
        .join(Partner, Partner.id == Program.partner_id)
        .where(
            Program.status == ProgramStatus.PUBLISHED,
            Partner.status == PartnerStatus.ACTIVE,
        )
    )


async def search_catalog(
    session: AsyncSession,
    category: PartnerCategory | None = None,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[CatalogProgram]:
    stmt = _base_query()
    if category is not None:
        stmt = stmt.where(Partner.category == category)
    if query:
        like = f"%{query.lower()}%"
        stmt = stmt.where(func.lower(Partner.name).like(like))
    stmt = stmt.order_by(Partner.name.asc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return [CatalogProgram.model_validate(row, from_attributes=True) for row in result]


async def list_categories(session: AsyncSession) -> list[CatalogCategory]:
    stmt = (
        select(Partner.category, func.count(Program.id))
        .join(Program, Program.partner_id == Partner.id)
        .where(
            Program.status == ProgramStatus.PUBLISHED,
            Partner.status == PartnerStatus.ACTIVE,
        )
        .group_by(Partner.category)
    )
    result = await session.execute(stmt)
    counts: dict[PartnerCategory, int] = dict(result.all())
    return [
        CatalogCategory(code=cat, label=label, programs_count=counts.get(cat, 0))
        for cat, label in _CATEGORY_LABELS.items()
    ]
