"""program: extended settings + program_tier table

Revision ID: 0005_program_settings
Revises: 0004_analytics_projection
Create Date: 2026-05-17

Расширение таблицы program новыми настройками программ лояльности
и добавление таблицы program_tier для уровней лояльности.
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_program_settings"
down_revision = "0004_analytics_projection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Новые колонки в core.program ---
    op.add_column(
        "program",
        sa.Column("welcome_bonus_points", sa.Integer(), nullable=True),
        schema="core",
    )
    op.add_column(
        "program",
        sa.Column("birthday_bonus_points", sa.Integer(), nullable=True),
        schema="core",
    )
    op.add_column(
        "program",
        sa.Column(
            "birthday_bonus_days",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        schema="core",
    )
    op.add_column(
        "program",
        sa.Column("referral_bonus_points", sa.Integer(), nullable=True),
        schema="core",
    )
    op.add_column(
        "program",
        sa.Column("min_purchase_amount", sa.Integer(), nullable=True),
        schema="core",
    )
    op.add_column(
        "program",
        sa.Column("max_points_per_transaction", sa.Integer(), nullable=True),
        schema="core",
    )
    op.add_column(
        "program",
        sa.Column("max_redemption_percent", sa.Integer(), nullable=True),
        schema="core",
    )
    op.add_column(
        "program",
        sa.Column("valid_from", sa.Date(), nullable=True),
        schema="core",
    )
    op.add_column(
        "program",
        sa.Column("valid_until", sa.Date(), nullable=True),
        schema="core",
    )

    # --- Таблица уровней лояльности ---
    op.create_table(
        "program_tier",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("program_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "threshold_points",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "accrual_multiplier",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["core.program.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_id", "name", name="uq_program_tier_name"),
        sa.UniqueConstraint(
            "program_id", "threshold_points", name="uq_program_tier_threshold"
        ),
        schema="core",
    )
    op.create_index(
        "ix_program_tier_program_id",
        "program_tier",
        ["program_id"],
        schema="core",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_program_tier_program_id", table_name="program_tier", schema="core"
    )
    op.drop_table("program_tier", schema="core")

    for col in [
        "welcome_bonus_points",
        "birthday_bonus_points",
        "birthday_bonus_days",
        "referral_bonus_points",
        "min_purchase_amount",
        "max_points_per_transaction",
        "max_redemption_percent",
        "valid_from",
        "valid_until",
    ]:
        op.drop_column("program", col, schema="core")
