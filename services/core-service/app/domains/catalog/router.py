from fastapi import APIRouter, Query

from app.deps import SessionDep
from app.domains.catalog import service
from app.domains.catalog.schemas import CatalogCategory, CatalogProgram
from app.domains.partners.models import PartnerCategory

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/programs", response_model=list[CatalogProgram])
async def search_programs(
    session: SessionDep,
    category: PartnerCategory | None = None,
    q: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[CatalogProgram]:
    return await service.search_catalog(
        session, category=category, query=q, limit=limit, offset=offset
    )


@router.get("/categories", response_model=list[CatalogCategory])
async def list_categories(session: SessionDep) -> list[CatalogCategory]:
    return await service.list_categories(session)
