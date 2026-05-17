# core-service

Центральный сервис платформы лояльности. Отвечает за:

- программы лояльности и правила начисления, уровни (tiers) и бонусные настройки;
- каталог наград партнёров;
- начисление, списание, отмену и сгорание баллов;
- историю транзакций;
- профиль клиента, баланс и список подключённых программ;
- публичный каталог программ для клиентов;
- агрегаты аналитики для дашборда партнёра.

## Структура

```
app/
  config.py            настройки (pydantic-settings, префикс CORE_)
  database.py          async engine, Base, get_session, get_read_session (реплика)
  deps.py              FastAPI зависимости (customer/partner id, sessions)
  jwt_tokens.py        декодирование JWT кассира (HS256)
  errors.py            HTTP-ошибки домена
  events.py            Kafka-publisher (core.events)
  consumer.py          Kafka-consumer (partner.events + core.events)
  inbox.py             диспетчер входящих событий
  audience.py          резолв сегментов аудитории для рассылок
  internal_router.py   служебные ручки /internal
  main.py              сборка приложения и подключение роутеров
  models.py            реестр всех моделей для Alembic
  domains/
    partners/          снэпшот партнёра (источник истины — partner-service) + sync.py
    programs/          программы лояльности, уровни, переходы статусов
    rewards/           каталог наград
    catalog/           публичный каталог программ для клиентов (без своих таблиц)
    enrollments/       подключение клиента к программе, профиль клиента
    points/            начисление/списание/отмена + баланс + expiration.py (сгорание)
    transactions/      история и выборки
    analytics/         read-модель дашборда партнёра (projection.py вместо models.py)
alembic/               миграции (0001…0006)
```

Каждый домен оформлен vertical slice: `models.py`/`projection.py`, `schemas.py`, `service.py`, `router.py`.

## Аутентификация

- **Клиентские** ручки (`/balance`, `/catalog`, `/enrollments`, `/transactions`):
  заголовок `X-Customer-Id: <uuid>` от API Gateway (TODO: заменить на T-ID / JWT).
- **Партнёрские/кассовые** ручки (`/points`, `/programs`, `/rewards`, `/partner/*`):
  `Authorization: Bearer <jwt>` — JWT кассира (HS256, `typ=staff`, `pid=partner_id`;
  секрет `CORE_JWT_SECRET` ОБЯЗАН совпадать с `PARTNER_JWT_SECRET`). Токен выдаёт
  partner-service (`POST /staff/login`). Fallback `X-Partner-Id: <uuid>` — легаси-стаб
  ЛК партнёра, пока у него нет своего JWT (TODO).

## Запуск

```bash
# из корня репозитория
uv sync

# настроить БД
cp services/core-service/.env.example services/core-service/.env
# поправить CORE_DATABASE_URL под локальный Postgres

# миграции
cd services/core-service
uv run alembic upgrade head

# приложение
uv run uvicorn app.main:app --reload --port 8001
```

### API-документация

|                  | URL                                  |
|------------------|--------------------------------------|
| **Swagger UI**   | `http://localhost:8001/docs`         |
| **ReDoc**        | `http://localhost:8001/redoc`        |
| **OpenAPI JSON** | `http://localhost:8001/openapi.json` |

### Переменные окружения (префикс `CORE_`)

| Переменная                                   | По умолчанию                    | Назначение                                                  |
|----------------------------------------------|---------------------------------|-------------------------------------------------------------|
| `CORE_DATABASE_URL`                          | `…@localhost:5432/tbank_loyalt` | основной DSN (psycopg, async)                               |
| `CORE_DATABASE_REPLICA_URL`                  | —                               | DSN read-реплики (история/аналитика); пусто → всё в primary |
| `CORE_DB_SCHEMA`                             | `core`                          | схема сервиса                                               |
| `CORE_DB_POOL_SIZE` / `CORE_DB_MAX_OVERFLOW` | `20` / `20`                     | пул соединений                                              |
| `CORE_LOG_LEVEL`                             | `INFO`                          | уровень логирования                                         |
| `CORE_JWT_SECRET`                            | dev-секрет                      | HS256 для JWT кассира (= `PARTNER_JWT_SECRET`)              |
| `CORE_KAFKA_ENABLED`                         | `false`                         | вкл/выкл Kafka                                              |
| `CORE_KAFKA_BOOTSTRAP_SERVERS`               | `localhost:9092`                | брокеры                                                     |
| `CORE_KAFKA_SUBSCRIBE_TOPICS`                | `[partner.events, core.events]` | топики consumer'а                                           |
| `CORE_EXPIRE_JOB_ENABLED`                    | `false`                         | фоновый цикл сгорания баллов                                |
| `CORE_EXPIRE_JOB_INTERVAL_SECONDS`           | `3600`                          | период фонового цикла                                       |

## Эндпоинты

| Группа             | Ручки                                                                                                                                                          |
|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `partners`         | `POST /partners`, `GET /partners`, `GET /partners/{id}`, `PATCH /partners/{id}`                                                                                |
| `programs`         | `POST /programs`, `GET /programs`, `GET /programs/{id}`, `PATCH /programs/{id}`, `POST /programs/{id}/{publish,pause,archive}`, CRUD уровней/настроек          |
| `rewards`          | `POST/GET /programs/{id}/rewards`, `GET/PATCH/DELETE /rewards/{id}`                                                                                            |
| `catalog`          | `GET /catalog/programs`, `GET /catalog/programs/{id}`, `GET /catalog/categories`                                                                               |
| `enrollments`      | `POST /enrollments`, `GET /enrollments`, `GET /enrollments/{id}`, `PATCH`, `DELETE`                                                                            |
| `points` (касса)   | `POST /points/accrue`, `POST /points/redeem`, `POST /points/transactions/{id}/reverse`, `GET /points/lookup/{enrollment_id}`, `GET /points/lookup-code/{code}` |
| `balance` (клиент) | `GET /balance`, `GET /balance/{program_id}`                                                                                                                    |
| `transactions`     | `GET /transactions`, `GET /transactions/{id}` (клиент), `GET /partner/transactions` (партнёр)                                                                  |
| `analytics`        | `GET /partner/analytics`                                                                                                                                       |
| `internal`         | `GET /internal/partner-audience`, `POST /internal/events`, `POST /internal/jobs/expire-points`, `POST /internal/analytics/rebuild`                             |
| `meta`             | `GET /health`                                                                                                                                                  |

## Базовый сценарий (curl)

```bash
# 1. Партнёр создаётся (потом будет приходить из partner-service)
PARTNER_ID=$(curl -s localhost:8001/partners -d '{
  "inn":"7707083893","name":"Кофе Хауз","category":"food"
}' -H 'content-type: application/json' | jq -r .id)

# 2. Партнёр создаёт программу (5% от чека, баллы живут 90 дней)
PROGRAM_ID=$(curl -s localhost:8001/programs \
  -H "X-Partner-Id: $PARTNER_ID" -H 'content-type: application/json' \
  -d '{"name":"Кофейная карта","type":"accrual",
       "accrual_rule":{"percent":5},"points_ttl_days":90,"min_redemption":100}' \
  | jq -r .id)

# 3. Публикация
curl -X POST localhost:8001/programs/$PROGRAM_ID/publish \
  -H "X-Partner-Id: $PARTNER_ID"

# 4. Награда — бесплатный капучино за 300 баллов
curl localhost:8001/programs/$PROGRAM_ID/rewards \
  -H "X-Partner-Id: $PARTNER_ID" -H 'content-type: application/json' \
  -d '{"title":"Капучино в подарок","cost_points":300,
       "type":"free_item","value":{"item":"Капучино 250 мл"}}'

# 5. Клиент подключается
CUSTOMER_ID=$(uuidgen | tr 'A-Z' 'a-z')
curl localhost:8001/enrollments \
  -H "X-Customer-Id: $CUSTOMER_ID" -H 'content-type: application/json' \
  -d "{\"program_id\":\"$PROGRAM_ID\"}"

# 6. Касса начисляет баллы за покупку на 1200 ₽ (purchase_amount — рубли)
curl localhost:8001/points/accrue \
  -H "X-Partner-Id: $PARTNER_ID" -H 'content-type: application/json' \
  -d "{\"customer_id\":\"$CUSTOMER_ID\",\"program_id\":\"$PROGRAM_ID\",
       \"purchase_amount\":\"1200.00\"}"

# 7. Клиент смотрит баланс
curl localhost:8001/balance/$PROGRAM_ID -H "X-Customer-Id: $CUSTOMER_ID"
```

> На партнёрских ручках вместо `X-Partner-Id` в проде идёт `Authorization: Bearer <jwt кассира>`.

## Модель данных

- **partner** — снэпшот партнёра (источник истины — partner-service).
- **program** — программа лояльности: `accrual_rule` в JSONB, статусы DRAFT → PUBLISHED →
  PAUSED/ARCHIVED, бонусные поля (welcome/birthday/referral), лимиты
  (`min_purchase_amount`, `max_points_per_transaction`, `max_redemption_percent`),
  окно действия (`valid_from`/`valid_until`).
- **program_tier** — уровни программы (порог баллов → множитель начисления).
- **reward** — награды для конкретной программы.
- **customer** — клиент (id = T-ID).
- **enrollment** — связь клиента и программы; денормализованный `points_balance`,
  уникальный `short_code` (для поиска кассой по коду).
- **transaction** — операция (ACCRUAL / REDEMPTION / REVERSAL / EXPIRATION); таблица
  партиционирована `HASH(partner_id)` (миграция 0003), составной PK `(id, partner_id)`.
  Баланс обновляется атомарно вместе с записью транзакции под `SELECT … FOR UPDATE`
  на строке `enrollment`.
- **analytics_daily / analytics_heatmap / analytics_processed_event** — read-модель
  дашборда (проекция из событий `points.*`; `analytics_processed_event` даёт
  идемпотентный дедуп по `event_id`).

## Kafka

Publisher (`app/events.py`) и consumer (`app/consumer.py`) стартуют в
`lifespan`. При `CORE_KAFKA_ENABLED=false` publisher логирует события,
consumer не стартует — события эмулируются через `POST /internal/events`.

**Публикуем** (топик `core.events`):

| Тип               | Когда                                          | Слушает                              |
|-------------------|------------------------------------------------|--------------------------------------|
| `points.accrued`  | после успешного `POST /points/accrue`          | notification-service, аналитика core |
| `points.redeemed` | после успешного `POST /points/redeem`          | notification-service, аналитика core |
| `points.reversed` | после `POST /points/transactions/{id}/reverse` | notification-service, аналитика core |
| `points.expiring` | баллы скоро сгорят (предупреждение)            | notification-service                 |
| `points.expired`  | баллы сгорели по TTL                           | notification-service, аналитика core |

**Слушаем** (топики `partner.events` и `core.events`):

| Тип                                | Действие                                                    |
|------------------------------------|-------------------------------------------------------------|
| `partner.approved`                 | upsert локального снэпшота `core.partner` (id = partner_id) |
| `partner.updated`                  | то же — обновляются name/logo_url/brand_color/contact_*     |
| `partner.status_changed`           | то же — обновляется status                                  |
| `points.accrued/redeemed/reversed` | проекция в read-модель аналитики (идемпотентно)             |

Эмуляция входящего события без Kafka:

```bash
curl localhost:8001/internal/events -H 'content-type: application/json' -d '{
  "type": "partner.approved",
  "payload": {
    "partner_id": "00000000-0000-0000-0000-000000000001",
    "inn": "7707083893",
    "name": "Кофе Хауз",
    "category": "food",
    "status": "active"
  }
}'
```

## Сгорание баллов

Реализовано в `app/domains/points/expiration.py` (`run_expiration`): списывает
баллы с истёкшим `expires_at` транзакцией `EXPIRATION`, публикует `points.expiring`
(предупреждение) и `points.expired`. Запуск — фоновым циклом при
`CORE_EXPIRE_JOB_ENABLED=true` (период `CORE_EXPIRE_JOB_INTERVAL_SECONDS`) либо
вручную/по cron через `POST /internal/jobs/expire-points` (идемпотентно).

## TODO

- Событие `reward.available`, когда баланс впервые достиг стоимости награды.
- Реальная авторизация клиента (T-ID/JWT) вместо `X-Customer-Id`; JWT партнёра
  вместо легаси-fallback `X-Partner-Id`.
- Идемпотентность операций начисления/списания (`Idempotency-Key`).
- Полная геймификация (streak, день рождения, реферальная программа) — бонусные
  поля в `program` есть, но прикладная логика начисления реализована не для всех.
