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

SCHEMA = "admin"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    op.create_table(
        "admin_account",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("email", name="uq_admin_account_email"),
        schema=SCHEMA,
    )

    op.create_table(
        "category_override",
        sa.Column("code", sa.String(length=32), primary_key=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "featured_partner",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("partner_id", name="uq_featured_partner_partner_id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_featured_partner_partner_id",
        "featured_partner",
        ["partner_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "banner",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.String(length=2000), nullable=True),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("link_url", sa.String(length=1024), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("banner", schema=SCHEMA)
    op.drop_index(
        "ix_featured_partner_partner_id", table_name="featured_partner", schema=SCHEMA
    )
    op.drop_table("featured_partner", schema=SCHEMA)
    op.drop_table("category_override", schema=SCHEMA)
    op.drop_table("admin_account", schema=SCHEMA)
    op.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}"')
