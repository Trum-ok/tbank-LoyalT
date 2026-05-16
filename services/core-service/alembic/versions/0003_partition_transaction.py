"""partition transaction by HASH(partner_id)

Revision ID: 0003_partition_transaction
Revises: 0002_enrollment_short_code
Create Date: 2026-05-16

PostgreSQL не умеет ALTER обычной таблицы в партиционированную, поэтому:
  1. переименовываем transaction -> transaction_old;
  2. создаём новую transaction PARTITION BY HASH (partner_id);
  3. создаём N hash-секций;
  4. переливаем данные;
  5. удаляем transaction_old.

Последствия партиционирования (см. CLAUDE.md, решение зафиксировано):
  * PK становится составным (id, partner_id) — ключ секции обязан входить
    в каждый уникальный констрейнт;
  * self-FK reverses_id -> transaction.id СНИМАЕТСЯ (ссылаться на часть
    составного ключа нельзя). Колонка reverses_id остаётся, целостность
    по ней теперь на стороне приложения (domains.points.service.reverse).

Профиль ускорения: HASH по partner_id — partner-scoped запросы
(list_for_partner, аналитика, points) бьют в одну секцию.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_partition_transaction"
down_revision: str | Sequence[str] | None = "0002_enrollment_short_code"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "core"
PARTITIONS = 8

# Колонки в порядке, едином для CREATE и для INSERT ... SELECT.
_COLUMNS = (
    "id",
    "enrollment_id",
    "customer_id",
    "program_id",
    "partner_id",
    "type",
    "points",
    "purchase_amount",
    "reward_id",
    "reverses_id",
    "expires_at",
    "is_reversed",
    "description",
    "created_at",
    "updated_at",
)


def _create_partitioned_table() -> None:
    op.execute(f"""
        CREATE TABLE "{SCHEMA}".transaction (
            id UUID NOT NULL,
            enrollment_id UUID NOT NULL,
            customer_id UUID NOT NULL,
            program_id UUID NOT NULL,
            partner_id UUID NOT NULL,
            type VARCHAR(16) NOT NULL,
            points INTEGER NOT NULL,
            purchase_amount NUMERIC(14, 2),
            reward_id UUID,
            reverses_id UUID,
            expires_at TIMESTAMP,
            is_reversed BOOLEAN NOT NULL DEFAULT false,
            description VARCHAR(500),
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now(),
            CONSTRAINT pk_transaction PRIMARY KEY (id, partner_id),
            CONSTRAINT fk_transaction_enrollment
                FOREIGN KEY (enrollment_id)
                REFERENCES "{SCHEMA}".enrollment (id) ON DELETE CASCADE,
            CONSTRAINT fk_transaction_customer
                FOREIGN KEY (customer_id)
                REFERENCES "{SCHEMA}".customer (id) ON DELETE CASCADE,
            CONSTRAINT fk_transaction_program
                FOREIGN KEY (program_id)
                REFERENCES "{SCHEMA}".program (id) ON DELETE CASCADE,
            CONSTRAINT fk_transaction_partner
                FOREIGN KEY (partner_id)
                REFERENCES "{SCHEMA}".partner (id) ON DELETE CASCADE,
            CONSTRAINT fk_transaction_reward
                FOREIGN KEY (reward_id)
                REFERENCES "{SCHEMA}".reward (id) ON DELETE SET NULL
        ) PARTITION BY HASH (partner_id)
        """)
    for i in range(PARTITIONS):
        op.execute(
            f'CREATE TABLE "{SCHEMA}".transaction_p{i} '
            f'PARTITION OF "{SCHEMA}".transaction '
            f"FOR VALUES WITH (MODULUS {PARTITIONS}, REMAINDER {i})"
        )


def _create_indexes() -> None:
    # Доминирующий партнёрский паттерн: фильтр partner_id + сортировка по времени.
    op.create_index(
        "ix_transaction_partner_created",
        "transaction",
        ["partner_id", "created_at"],
        schema=SCHEMA,
    )
    # История клиента: customer_id (+ program_id) + сортировка по времени.
    op.create_index(
        "ix_transaction_customer_prog_created",
        "transaction",
        ["customer_id", "program_id", "created_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_transaction_enrollment_id",
        "transaction",
        ["enrollment_id"],
        schema=SCHEMA,
    )
    # Сканер сгорания: только живые начисления со сроком.
    op.execute(
        f'CREATE INDEX ix_transaction_expires_at ON "{SCHEMA}".transaction '
        "(expires_at) WHERE is_reversed = false AND type = 'accrual'"
    )


def upgrade() -> None:
    cols = ", ".join(_COLUMNS)

    op.execute(f'ALTER TABLE "{SCHEMA}".transaction RENAME TO transaction_old')
    _create_partitioned_table()
    op.execute(
        f'INSERT INTO "{SCHEMA}".transaction ({cols}) '
        f'SELECT {cols} FROM "{SCHEMA}".transaction_old'
    )
    op.execute(f'DROP TABLE "{SCHEMA}".transaction_old')
    _create_indexes()


def downgrade() -> None:
    cols = ", ".join(_COLUMNS)

    op.execute(f'ALTER TABLE "{SCHEMA}".transaction RENAME TO transaction_part')
    # Обычная (непартиционированная) таблица с исходным PK и self-FK.
    op.execute(f"""
        CREATE TABLE "{SCHEMA}".transaction (
            id UUID NOT NULL,
            enrollment_id UUID NOT NULL,
            customer_id UUID NOT NULL,
            program_id UUID NOT NULL,
            partner_id UUID NOT NULL,
            type VARCHAR(16) NOT NULL,
            points INTEGER NOT NULL,
            purchase_amount NUMERIC(14, 2),
            reward_id UUID,
            reverses_id UUID,
            expires_at TIMESTAMP,
            is_reversed BOOLEAN NOT NULL DEFAULT false,
            description VARCHAR(500),
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now(),
            CONSTRAINT pk_transaction PRIMARY KEY (id),
            CONSTRAINT fk_transaction_enrollment
                FOREIGN KEY (enrollment_id)
                REFERENCES "{SCHEMA}".enrollment (id) ON DELETE CASCADE,
            CONSTRAINT fk_transaction_customer
                FOREIGN KEY (customer_id)
                REFERENCES "{SCHEMA}".customer (id) ON DELETE CASCADE,
            CONSTRAINT fk_transaction_program
                FOREIGN KEY (program_id)
                REFERENCES "{SCHEMA}".program (id) ON DELETE CASCADE,
            CONSTRAINT fk_transaction_partner
                FOREIGN KEY (partner_id)
                REFERENCES "{SCHEMA}".partner (id) ON DELETE CASCADE,
            CONSTRAINT fk_transaction_reward
                FOREIGN KEY (reward_id)
                REFERENCES "{SCHEMA}".reward (id) ON DELETE SET NULL,
            CONSTRAINT fk_transaction_reverses
                FOREIGN KEY (reverses_id)
                REFERENCES "{SCHEMA}".transaction (id) ON DELETE SET NULL
        )
        """)
    op.execute(
        f'INSERT INTO "{SCHEMA}".transaction ({cols}) '
        f'SELECT {cols} FROM "{SCHEMA}".transaction_part'
    )
    op.execute(f'DROP TABLE "{SCHEMA}".transaction_part')

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
