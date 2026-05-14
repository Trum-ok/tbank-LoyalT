"""Реестр моделей admin-service для Alembic.

Метрики читают чужие схемы через сырой SQL — модели туда не нужны.
"""

from app.domains.admins.models import AdminAccount
from app.domains.catalog.models import Banner, CategoryOverride, FeaturedPartner

__all__ = ["AdminAccount", "Banner", "CategoryOverride", "FeaturedPartner"]
