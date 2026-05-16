"""staff (кассиры партнёра)

Revision ID: 0002_staff
Revises: 0001_initial
Create Date: 2026-05-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_staff"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "partner"

# Демо-кассир для демо-партнёра "Кофе Хауз" (см. frontend/partner identity).
# PIN = 0000, login_code = COFFEE. Вставляется только если такой партнёр есть.
DEMO_PARTNER_ID = "1f6ea13f-7ddb-4a0a-82e9-6308a2616267"
DEMO_STAFF_ID = "aaaaaaaa-0000-0000-0000-000000000001"
DEMO_PIN_HASH = (
    "pbkdf2_sha256$240000$50b5477511bece0b7672ce28c3d9690e$"
    "579e89c379077628e294a9c628cb8da6b9297e7e07dac9c591ab41d3a54dc52f"
)


def upgrade() -> None:
    op.create_table(
        "staff",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("login_code", sa.String(length=32), nullable=False),
        sa.Column("pin_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"], [f"{SCHEMA}.partner.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("login_code", name="uq_staff_login_code"),
        schema=SCHEMA,
    )
    op.create_index("ix_staff_partner_id", "staff", ["partner_id"], schema=SCHEMA)

    op.execute(
        sa.text(f"""
            INSERT INTO "{SCHEMA}".staff
                (id, partner_id, name, login_code, pin_hash, is_active)
            SELECT
                CAST(:staff_id AS uuid), CAST(:partner_id AS uuid),
                'Касса (демо)', 'COFFEE', :pin_hash, true
            WHERE EXISTS (
                SELECT 1 FROM "{SCHEMA}".partner
                WHERE id = CAST(:partner_id AS uuid)
            )
            """).bindparams(
            staff_id=DEMO_STAFF_ID,
            partner_id=DEMO_PARTNER_ID,
            pin_hash=DEMO_PIN_HASH,
        )
    )


def downgrade() -> None:
    op.drop_index("ix_staff_partner_id", table_name="staff", schema=SCHEMA)
    op.drop_table("staff", schema=SCHEMA)
