"""enrollment.short_code (цифровой код для кассы)

Revision ID: 0002_enrollment_short_code
Revises: 0001_initial
Create Date: 2026-05-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_enrollment_short_code"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "core"


def upgrade() -> None:
    op.add_column(
        "enrollment",
        sa.Column("short_code", sa.String(length=12), nullable=True),
        schema=SCHEMA,
    )

    # Backfill: последовательный код каждому существующему подключению,
    # начиная с 1000 (минимум 4 цифры).
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(f'SELECT id FROM "{SCHEMA}".enrollment ORDER BY created_at')
    ).fetchall()
    for offset, (enrollment_id,) in enumerate(rows):
        bind.execute(
            sa.text(
                f'UPDATE "{SCHEMA}".enrollment '
                "SET short_code = :code WHERE id = :id"
            ).bindparams(code=str(1000 + offset), id=enrollment_id)
        )

    op.alter_column(
        "enrollment", "short_code", nullable=False, schema=SCHEMA
    )
    op.create_unique_constraint(
        "uq_enrollment_short_code", "enrollment", ["short_code"], schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_enrollment_short_code", "enrollment", schema=SCHEMA, type_="unique"
    )
    op.drop_column("enrollment", "short_code", schema=SCHEMA)
