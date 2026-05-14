from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domains.partners.models import PartnerCategory
from app.domains.programs.models import ProgramType


class CatalogProgram(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    program_id: UUID
    partner_id: UUID
    partner_name: str
    partner_logo_url: str | None
    partner_brand_color: str | None
    category: PartnerCategory
    program_name: str
    description: str | None
    type: ProgramType


class CatalogCategory(BaseModel):
    code: PartnerCategory
    label: str
    programs_count: int
