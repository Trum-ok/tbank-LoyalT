"""broadcast (рассылки партнёра)

Revision ID: 0003_broadcast
Revises: 0002_staff
Create Date: 2026-05-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_broadcast"
down_revision: str | Sequence[str] | None = "0002_staff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "partner"


def upgrade() -> None:
    op.create_table(
        "broadcast",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("segment", sa.String(length=32), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("audience_count", sa.Integer(), nullable=True),
        sa.Column("sent_count", sa.Integer(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_broadcast_partner_id", "broadcast", ["partner_id"], schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_index("ix_broadcast_partner_id", table_name="broadcast", schema=SCHEMA)
    op.drop_table("broadcast", schema=SCHEMA)
