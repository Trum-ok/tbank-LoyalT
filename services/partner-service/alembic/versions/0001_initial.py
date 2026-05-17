"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "partner"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    op.create_table(
        "account",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("email", name="uq_account_email"),
        schema=SCHEMA,
    )

    op.create_table(
        "application",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("business_name", sa.String(length=255), nullable=False),
        sa.Column("inn", sa.String(length=12), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("decision_comment", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], [f"{SCHEMA}.account.id"], ondelete="CASCADE"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_application_account_id", "application", ["account_id"], schema=SCHEMA
    )
    op.create_index("ix_application_status", "application", ["status"], schema=SCHEMA)

    op.create_table(
        "partner",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("inn", sa.String(length=12), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("logo_url", sa.String(length=1024), nullable=True),
        sa.Column("brand_color", sa.String(length=16), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["account_id"], [f"{SCHEMA}.account.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], [f"{SCHEMA}.application.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("account_id", name="uq_partner_account"),
        sa.UniqueConstraint("application_id", name="uq_partner_application"),
        sa.UniqueConstraint("inn", name="uq_partner_inn"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("partner", schema=SCHEMA)
    op.drop_table("application", schema=SCHEMA)
    op.drop_table("account", schema=SCHEMA)
    op.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}"')
