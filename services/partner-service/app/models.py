"""Реестр моделей для Alembic autogenerate."""

from app.domains.accounts.models import Account
from app.domains.applications.models import Application
from app.domains.partners.models import Partner

__all__ = ["Account", "Application", "Partner"]
