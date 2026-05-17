"""customer.birthday + bonus_trigger + bonus_trigger_log

Revision ID: 0007_bonus_campaigns
Revises: 0006_points_expiration
Create Date: 2026-05-17

Добавляет:
  * customer.birthday DATE — дата рождения клиента для birthday-кампаний
  * core.bonus_trigger — бонусные кампании (условия авто-начисления)
  * core.bonus_trigger_log — журнал срабатываний кампаний
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_bonus_campaigns"
down_revision: str | Sequence[str] | None = "0006_points_expiration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "core"


def upgrade() -> None:
    # ── customer.birthday ─────────────────────────────────────────────────
    op.add_column(
        "customer",
        sa.Column("birthday", sa.Date(), nullable=True),
        schema=SCHEMA,
    )

    # ── bonus_trigger ─────────────────────────────────────────────────────
    op.create_table(
        "bonus_trigger",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "program_id",
            sa.UUID(),
            sa.ForeignKey(f"{SCHEMA}.program.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column("days_before", sa.Integer(), nullable=True),
        sa.Column("fire_date", sa.Date(), nullable=True),
        sa.Column(
            "repeat_yearly",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("interval_days", sa.Integer(), nullable=True),
        sa.Column(
            "repeat_interval",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_bonus_trigger_program_id",
        "bonus_trigger",
        ["program_id"],
        schema=SCHEMA,
    )

    # ── bonus_trigger_log ─────────────────────────────────────────────────
    op.create_table(
        "bonus_trigger_log",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column(
            "trigger_id",
            sa.UUID(),
            sa.ForeignKey(f"{SCHEMA}.bonus_trigger.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "enrollment_id",
            sa.UUID(),
            sa.ForeignKey(f"{SCHEMA}.enrollment.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "fired_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_bonus_trigger_log_trigger_enrollment",
        "bonus_trigger_log",
        ["trigger_id", "enrollment_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_bonus_trigger_log_trigger_enrollment",
        table_name="bonus_trigger_log",
        schema=SCHEMA,
    )
    op.drop_table("bonus_trigger_log", schema=SCHEMA)

    op.drop_index(
        "ix_bonus_trigger_program_id",
        table_name="bonus_trigger",
        schema=SCHEMA,
    )
    op.drop_table("bonus_trigger", schema=SCHEMA)

    op.drop_column("customer", "birthday", schema=SCHEMA)
