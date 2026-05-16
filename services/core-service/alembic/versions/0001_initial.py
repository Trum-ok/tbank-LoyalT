"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "core"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    op.create_table(
        "partner",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("inn", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("logo_url", sa.String(length=1024), nullable=True),
        sa.Column("brand_color", sa.String(length=16), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("inn", name="uq_partner_inn"),
        schema=SCHEMA,
    )

    op.create_table(
        "customer",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "program",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column(
            "accrual_rule",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("points_ttl_days", sa.Integer(), nullable=True),
        sa.Column("min_redemption", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="draft"
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"], [f"{SCHEMA}.partner.id"], ondelete="CASCADE"
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_program_partner_id", "program", ["partner_id"], schema=SCHEMA)
    op.create_index("ix_program_status", "program", ["status"], schema=SCHEMA)

    op.create_table(
        "reward",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("cost_points", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column(
            "value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["program_id"], [f"{SCHEMA}.program.id"], ondelete="CASCADE"
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_reward_program_id", "reward", ["program_id"], schema=SCHEMA)

    op.create_table(
        "enrollment",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("points_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], [f"{SCHEMA}.customer.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["program_id"], [f"{SCHEMA}.program.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "customer_id", "program_id", name="uq_enrollment_customer_program"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_enrollment_customer_id", "enrollment", ["customer_id"], schema=SCHEMA
    )
    op.create_index(
        "ix_enrollment_program_id", "enrollment", ["program_id"], schema=SCHEMA
    )

    op.create_table(
        "transaction",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("purchase_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("reward_id", sa.Uuid(), nullable=True),
        sa.Column("reverses_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_reversed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], [f"{SCHEMA}.enrollment.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], [f"{SCHEMA}.customer.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["program_id"], [f"{SCHEMA}.program.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"], [f"{SCHEMA}.partner.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reward_id"], [f"{SCHEMA}.reward.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["reverses_id"], [f"{SCHEMA}.transaction.id"], ondelete="SET NULL"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_transaction_customer_id", "transaction", ["customer_id"], schema=SCHEMA
    )
    op.create_index(
        "ix_transaction_program_id", "transaction", ["program_id"], schema=SCHEMA
    )
    op.create_index(
        "ix_transaction_enrollment_id",
        "transaction",
        ["enrollment_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_transaction_expires_at", "transaction", ["expires_at"], schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_table("transaction", schema=SCHEMA)
    op.drop_table("enrollment", schema=SCHEMA)
    op.drop_table("reward", schema=SCHEMA)
    op.drop_table("program", schema=SCHEMA)
    op.drop_table("customer", schema=SCHEMA)
    op.drop_table("partner", schema=SCHEMA)
    op.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}"')
