"""points expiration: program.expire_warn_days + transaction.expiry_warned

Revision ID: 0006_points_expiration
Revises: 0005_program_settings
Create Date: 2026-05-17

Сгорание баллов по TTL уже моделировалось (program.points_ttl_days,
transaction.expires_at, TransactionType.EXPIRATION). Эта миграция
добавляет:

  * program.expire_warn_days — за сколько дней до сгорания слать push;
  * transaction.expiry_warned — флаг «предупреждение уже отправлено»,
    чтобы джоб не дублировал уведомление каждый прогон.

transaction партиционирована HASH(partner_id) (миграция 0003);
ALTER TABLE ... ADD COLUMN на родительской таблице каскадно
применяется ко всем секциям (PostgreSQL 11+).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_points_expiration"
down_revision: str | Sequence[str] | None = "0005_program_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "core"


def upgrade() -> None:
    op.add_column(
        "program",
        sa.Column("expire_warn_days", sa.Integer(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "transaction",
        sa.Column(
            "expiry_warned",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("transaction", "expiry_warned", schema=SCHEMA)
    op.drop_column("program", "expire_warn_days", schema=SCHEMA)
