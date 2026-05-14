"""Реестр моделей для Alembic autogenerate."""

from app.domains.devices.models import Device
from app.domains.notifications.models import Notification

__all__ = ["Device", "Notification"]
