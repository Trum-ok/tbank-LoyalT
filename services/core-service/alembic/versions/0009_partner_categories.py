"""multi-category: core.partner_category

Revision ID: 0008_partner_categories
Revises: 0007_idempotency_key
Create Date: 2026-05-17

Снэпшот партнёра в core теперь хранит несколько категорий в join-таблице
`partner_category`. Существующее значение `partner.category` переносится
одной строкой, затем колонка удаляется. Источник истины — partner-service,
синхронизация идёт событиями `partner.events` (см. domains/partners/sync.py).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_partner_categories"
down_revision: str | Sequence[str] | None = "0008_idempotency_key"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "core"


def upgrade() -> None:
    op.create_table(
        "partner_category",
        sa.Column("partner_id", sa.Uuid(), primary_key=True),
        sa.Column("category", sa.String(length=32), primary_key=True),
        sa.ForeignKeyConstraint(
            ["partner_id"], [f"{SCHEMA}.partner.id"], ondelete="CASCADE"
        ),
        schema=SCHEMA,
    )
    op.execute(
        f"INSERT INTO {SCHEMA}.partner_category (partner_id, category) "
        f"SELECT id, category FROM {SCHEMA}.partner"
    )
    op.drop_column("partner", "category", schema=SCHEMA)


def downgrade() -> None:
    op.add_column(
        "partner",
        sa.Column("category", sa.String(length=32), nullable=True),
        schema=SCHEMA,
    )
    op.execute(
        f"UPDATE {SCHEMA}.partner p SET category = ("
        f"  SELECT category FROM {SCHEMA}.partner_category pc "
        f"  WHERE pc.partner_id = p.id ORDER BY category LIMIT 1)"
    )
    op.execute(
        f"UPDATE {SCHEMA}.partner SET category = 'services' WHERE category IS NULL"
    )
    op.alter_column("partner", "category", nullable=False, schema=SCHEMA)
    op.drop_table("partner_category", schema=SCHEMA)
