# deploy/

Локальный запуск всей платформы через docker-compose.

## Что поднимается

| Контейнер | Порт хоста | Назначение |
|---|---|---|
| `postgres` | 5433 | PostgreSQL 16, одна БД `tbank_loyalt`, schema-per-service (5433 на хосте, чтобы не конфликтовать с локальным Postgres) |
| `kafka` | 9092 | Apache Kafka 3.7.1 (KRaft, без ZooKeeper), auto-create topics |
| `core-service` | 8001 | программы лояльности, баллы, транзакции |
| `partner-service` | 8002 | ЛК партнёра, заявки, профиль |
| `notification-service` | 8003 | push-уведомления (stub-доставка) |
| `admin-service` | 8004 | админ-панель Т-Банка |

## Команды

```bash
cd deploy

# Поднять весь стек (первый запуск собирает образ ~3-5 мин)
docker compose up --build

# В фоне
docker compose up -d --build

# Логи одного сервиса
docker compose logs -f notification-service

# Остановить
docker compose down

# Остановить + удалить тома (полный сброс БД и Kafka)
docker compose down -v
```

Каждый сервис на старте делает `alembic upgrade head` и поднимает uvicorn.

## Архитектура

```
                          ┌────────────────────────┐
                          │       PostgreSQL       │
                          │  schemas: core,        │
                          │  partner, notification,│
                          │  admin                 │
                          └────────────────────────┘
                                    ▲ ▲ ▲ ▲
                          ┌─────────┘ │ │ └──────────────┐
                          │           │ │                │
   ┌──────────────────────┴───┐  ┌────┴─┴─────────┐  ┌───┴────────────────┐
   │       core-service       │  │ partner-service│  │  notification-svc  │
   │  publishes: points.*     │  │ publishes:     │  │  consumes: core.+  │
   │  consumes: partner.events│  │  partner.events│  │  partner.events    │
   └────────┬────────────┬────┘  └────────┬───────┘  └────────────────────┘
            │            │                │                      ▲
            │   core.    │                │  partner.            │
            │  events    │                │   events             │
            ▼            ▼                ▼                      │
        ┌──────────────────────────────────────────┐             │
        │                  Kafka                   │─────────────┘
        └──────────────────────────────────────────┘

   admin-service ──HTTP──▶ partner-service        (модерация — прокси)
   admin-service ──SQL──▶  core.* / partner.*     (метрики — read-only)
```

## Базовый сценарий

После `docker compose up --build` подождать ~30 секунд, пока все
healthchecks станут `healthy`, и:

```bash
# 1. Создать первого админа (bootstrap)
ADMIN=$(curl -s localhost:8004/admins \
  -H 'content-type: application/json' \
  -d '{"email":"root@tbank.ru","full_name":"Admin"}' | jq -r .id)

# 2. Партнёр заводит аккаунт и подаёт заявку
ACC=$(curl -s localhost:8002/accounts -H 'content-type: application/json' \
  -d '{"email":"owner@cafe.ru","full_name":"Иван"}' | jq -r .id)
APP=$(curl -s localhost:8002/applications -H "X-Account-Id: $ACC" \
  -H 'content-type: application/json' -d '{
    "business_name":"Кофе Хауз","inn":"7707083893","category":"food",
    "contact_email":"hello@cafe.ru"
  }' | jq -r .id)

# 3. Админ одобряет через admin-service (прокси в partner-service).
#    partner-service публикует partner.approved → core-service подхватит.
PARTNER=$(curl -s localhost:8004/moderation/applications/$APP/approve \
  -H "X-Admin-Id: $ADMIN" -H 'content-type: application/json' \
  -d '{"comment":"OK"}' | jq -r .id)

# Подождать пару секунд, пока core применит событие, и проверить:
curl localhost:8001/partners/$PARTNER

# 4. Создаём программу и публикуем (партнёрские ручки core)
PROGRAM=$(curl -s localhost:8001/programs \
  -H "X-Partner-Id: $PARTNER" -H 'content-type: application/json' \
  -d '{"name":"Кофейная карта","type":"accrual",
       "accrual_rule":{"percent":5},"min_redemption":100}' | jq -r .id)
curl -X POST localhost:8001/programs/$PROGRAM/publish -H "X-Partner-Id: $PARTNER"

# 5. Клиент регистрирует устройство в notification-service
CUSTOMER=$(uuidgen | tr 'A-Z' 'a-z')
curl localhost:8003/devices -H "X-Customer-Id: $CUSTOMER" \
  -H 'content-type: application/json' \
  -d '{"token":"fcm_demo_token_xyz","platform":"android"}'

# 6. Клиент подключается к программе
curl localhost:8001/enrollments -H "X-Customer-Id: $CUSTOMER" \
  -H 'content-type: application/json' \
  -d "{\"program_id\":\"$PROGRAM\"}"

# 7. Партнёр начисляет баллы на кассе.
#    Это публикует points.accrued → notification-service создаст push.
curl localhost:8001/points/accrue -H "X-Partner-Id: $PARTNER" \
  -H 'content-type: application/json' \
  -d "{\"customer_id\":\"$CUSTOMER\",\"program_id\":\"$PROGRAM\",\"purchase_amount\":\"1200.00\"}"

# 8. Клиент видит свой баланс и уведомление
curl localhost:8001/balance/$PROGRAM -H "X-Customer-Id: $CUSTOMER"
curl localhost:8003/notifications -H "X-Customer-Id: $CUSTOMER"

# 9. Метрики платформы
curl localhost:8004/metrics/overview -H "X-Admin-Id: $ADMIN"
```

## Отладка Kafka

Auto-create topics включен; топики создадутся при первой записи.

```bash
# Список топиков
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --list

# Слушать события из core
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic core.events --from-beginning
```

## Перезапуск одного сервиса после правки кода

Кэш слоёв Dockerfile построен так, что изменение `services/**` не
переустанавливает зависимости (этот слой кеширован по `pyproject.toml`).

```bash
docker compose build core-service && docker compose up -d core-service
```

Для итеративной разработки удобнее запускать сервис локально через
`uv run uvicorn app.main:app --reload`, оставив в compose только
postgres + kafka.
