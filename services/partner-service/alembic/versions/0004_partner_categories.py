"""multi-category: application_category + partner_category

Revision ID: 0004_partner_categories
Revises: 0003_broadcast
Create Date: 2026-05-17

Партнёр (и заявка) теперь может относиться к нескольким категориям.
Единственная колонка `category` заменяется join-таблицами; существующие
данные переносятся одной строкой на сущность, затем колонка удаляется.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_partner_categories"
down_revision: str | Sequence[str] | None = "0003_broadcast"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "partner"


def upgrade() -> None:
    op.create_table(
        "application_category",
        sa.Column("application_id", sa.Uuid(), primary_key=True),
        sa.Column("category", sa.String(length=32), primary_key=True),
        sa.ForeignKeyConstraint(
            ["application_id"], [f"{SCHEMA}.application.id"], ondelete="CASCADE"
        ),
        schema=SCHEMA,
    )
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
        f"INSERT INTO {SCHEMA}.application_category (application_id, category) "
        f"SELECT id, category FROM {SCHEMA}.application"
    )
    op.execute(
        f"INSERT INTO {SCHEMA}.partner_category (partner_id, category) "
        f"SELECT id, category FROM {SCHEMA}.partner"
    )

    op.drop_column("application", "category", schema=SCHEMA)
    op.drop_column("partner", "category", schema=SCHEMA)


def downgrade() -> None:
    op.add_column(
        "application",
        sa.Column("category", sa.String(length=32), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "partner",
        sa.Column("category", sa.String(length=32), nullable=True),
        schema=SCHEMA,
    )
    # Восстанавливаем единственную категорию (первую по алфавиту).
    op.execute(
        f"UPDATE {SCHEMA}.application a SET category = ("
        f"  SELECT category FROM {SCHEMA}.application_category ac "
        f"  WHERE ac.application_id = a.id ORDER BY category LIMIT 1)"
    )
    op.execute(
        f"UPDATE {SCHEMA}.partner p SET category = ("
        f"  SELECT category FROM {SCHEMA}.partner_category pc "
        f"  WHERE pc.partner_id = p.id ORDER BY category LIMIT 1)"
    )
    op.alter_column("application", "category", nullable=False, schema=SCHEMA)
    op.alter_column("partner", "category", nullable=False, schema=SCHEMA)

    op.drop_table("partner_category", schema=SCHEMA)
    op.drop_table("application_category", schema=SCHEMA)
