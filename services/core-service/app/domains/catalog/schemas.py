from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domains.partners.models import PartnerCategory
from app.domains.programs.models import ProgramType
from app.domains.programs.schemas import TierRead
from app.domains.rewards.schemas import RewardRead


class CatalogProgram(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    program_id: UUID
    partner_id: UUID
    partner_name: str
    partner_logo_url: str | None
    partner_brand_color: str | None
    categories: list[PartnerCategory]
    program_name: str
    description: str | None
    type: ProgramType


class CatalogProgramDetail(CatalogProgram):
    accrual_rule: dict[str, Any]
    points_ttl_days: int | None
    min_redemption: int
    tiers: list[TierRead] = []
    rewards: list[RewardRead] = []


class CatalogCategory(BaseModel):
    code: PartnerCategory
    label: str
    programs_count: int
