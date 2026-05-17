"""idempotency: transaction.idempotency_key + request_fingerprint

Revision ID: 0007_idempotency_key
Revises: 0006_points_expiration
Create Date: 2026-05-17

Идемпотентность операций начисления/списания. Касса/ЛК передаёт
заголовок Idempotency-Key; повтор того же ключа возвращает результат
первой операции, не дублируя баллы. request_fingerprint (sha256
канонического тела) ловит переиспользование ключа с другим телом → 409.

transaction партиционирована HASH(partner_id) (миграция 0003);
ALTER TABLE ... ADD COLUMN на родительской таблице каскадно
применяется ко всем секциям (PostgreSQL 11+).

Уникальный индекс — обычный (не partial): partial-unique на
партиционированной таблице PostgreSQL не поддерживает. partner_id
входит в ключ (требование партиционирования), а NULL в unique-индексе
считается различным, поэтому строки без idempotency_key (reverse,
expiration, accrual без заголовка) не конфликтуют между собой.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_idempotency_key"
down_revision: str | Sequence[str] | None = "0007_" # TODO
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "core"


def upgrade() -> None:
    op.add_column(
        "transaction",
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "transaction",
        sa.Column("request_fingerprint", sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_transaction_idempotency",
        "transaction",
        ["partner_id", "idempotency_key"],
        unique=True,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("uq_transaction_idempotency", "transaction", schema=SCHEMA)
    op.drop_column("transaction", "request_fingerprint", schema=SCHEMA)
    op.drop_column("transaction", "idempotency_key", schema=SCHEMA)
