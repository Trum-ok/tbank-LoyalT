"""Реестр SQLAlchemy-моделей для Alembic autogenerate.

Импорт всех модулей с моделями обязателен, чтобы они зарегистрировались
в `Base.metadata` до того, как Alembic сравнит схему.
"""

from app.domains.analytics.projection import (
    AnalyticsDaily,
    AnalyticsHeatmap,
    AnalyticsProcessedEvent,
)
from app.domains.enrollments.models import Customer, Enrollment
from app.domains.partners.models import Partner
from app.domains.programs.models import (
    BonusTrigger,
    BonusTriggerLog,
    Program,
    ProgramTier,
)
from app.domains.rewards.models import Reward
from app.domains.transactions.models import Transaction

__all__ = [
    "AnalyticsDaily",
    "AnalyticsHeatmap",
    "AnalyticsProcessedEvent",
    "BonusTrigger",
    "BonusTriggerLog",
    "Customer",
    "Enrollment",
    "Partner",
    "Program",
    "ProgramTier",
    "Reward",
    "Transaction",
]
