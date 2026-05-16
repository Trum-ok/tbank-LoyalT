"""analytics projection tables (read model)

Revision ID: 0004_analytics_projection
Revises: 0003_partition_transaction
Create Date: 2026-05-16

Проекция потока событий points.* на read-модель дашборда. Дашборд
читает эти таблицы вместо скана transaction. Наполняется инкрементально
консьюмером (idempotent по analytics_processed_event) и/или пересобирается
из transaction (источник истины) джобой rebuild_analytics_projection.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_analytics_projection"
down_revision: str | Sequence[str] | None = "0003_partition_transaction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "core"


def upgrade() -> None:
    # Дневной агрегат по (партнёр, клиент, день). Наличие строки = клиент
    # был активен в этот день (нереверсная операция).
    op.create_table(
        "analytics_daily",
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("accrual_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accrued_points", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("redeemed_points", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "purchase_amount_sum",
            sa.Numeric(18, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("purchase_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("partner_id", "customer_id", "day"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_analytics_daily_partner_day",
        "analytics_daily",
        ["partner_id", "day"],
        schema=SCHEMA,
    )

    # Heatmap: счётчик нереверсных операций по (партнёр, день, час).
    # День недели выводится из day при чтении; day нужен для фильтра периода.
    op.create_table(
        "analytics_heatmap",
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("hour", sa.SmallInteger(), nullable=False),
        sa.Column("cnt", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("partner_id", "day", "hour"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_analytics_heatmap_partner_day",
        "analytics_heatmap",
        ["partner_id", "day"],
        schema=SCHEMA,
    )

    # Дедуп входящих событий (at-least-once Kafka). Ключ — id транзакции
    # из payload (для reversal — id самой reversal-операции).
    op.create_table(
        "analytics_processed_event",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("event_id"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("analytics_processed_event", schema=SCHEMA)
    op.drop_table("analytics_heatmap", schema=SCHEMA)
    op.drop_table("analytics_daily", schema=SCHEMA)
