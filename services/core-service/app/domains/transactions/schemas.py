from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domains.transactions.models import TransactionType


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    enrollment_id: UUID
    customer_id: UUID
    program_id: UUID
    partner_id: UUID
    type: TransactionType
    points: int
    purchase_amount: Decimal | None
    reward_id: UUID | None
    reverses_id: UUID | None
    expires_at: datetime | None
    is_reversed: bool
    description: str | None
    created_at: datetime
