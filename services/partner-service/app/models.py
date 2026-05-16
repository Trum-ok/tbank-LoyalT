"""Реестр моделей для Alembic autogenerate."""

from app.domains.accounts.models import Account
from app.domains.applications.models import Application
from app.domains.broadcasts.models import Broadcast
from app.domains.partners.models import Partner
from app.domains.staff.models import Staff

__all__ = ["Account", "Application", "Broadcast", "Partner", "Staff"]
