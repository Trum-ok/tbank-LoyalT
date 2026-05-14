from datetime import date
from uuid import UUID

from pydantic import BaseModel


class PartnersOverview(BaseModel):
    total: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    pending_applications: int


class CustomersOverview(BaseModel):
    total: int
    enrolled: int  # клиенты с хотя бы одним подключением


class TransactionsOverview(BaseModel):
    accruals_count: int
    accruals_points: int
    redemptions_count: int
    redemptions_points: int
    reversals_count: int


class TopPartner(BaseModel):
    partner_id: UUID
    partner_name: str
    transactions_count: int
    customers_count: int


class DailyCount(BaseModel):
    day: date
    count: int


class PlatformOverview(BaseModel):
    partners: PartnersOverview
    customers: CustomersOverview
    transactions: TransactionsOverview
