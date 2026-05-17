# partner-service

ЛК партнёра: регистрация бизнеса, модерация, профиль одобренного партнёра,
кассиры (staff) с JWT, рассылки клиентам.

## Доменная модель

- **account** — учётная запись владельца ЛК (auth — заглушка через `X-Account-Id`).
- **application** — заявка на регистрацию бизнеса (`pending` → `approved` / `rejected`).
- **partner** — одобренный партнёр; источник истины. При одобрении заявки, обновлении
  профиля и смене статуса публикуется событие в Kafka (`partner.events`), которое
  слушает core-service и обновляет свой снэпшот.
- **staff** — кассиры/сотрудники партнёра; входят по логину/паролю и получают
  JWT (HS256), которым авторизуются на кассовых ручках core-service.
- **broadcast** — рассылка партнёра по сегменту аудитории; аудитория резолвится
  REST-запросом в core-service, отправка публикует событие `partner.broadcast`.

```
[account] 1—∞ [application] —approve→ [partner] —┬─ partner.approved      → Kafka
                                                 ├─ partner.updated       → Kafka
                                                 ├─ partner.status_changed → Kafka
                                                 ├─ [staff] (JWT кассира)
                                                 └─ [broadcast] —send→ partner.broadcast → Kafka
```

## Структура

```
app/
  config.py           pydantic-settings, префикс PARTNER_
  database.py         async engine, Base
  deps.py             X-Account-Id / X-Partner-Id / X-Admin-Id / Bearer-JWT кассира
  jwt_tokens.py       выпуск/проверка JWT кассира (HS256)
  storage.py          загрузка логотипов в MinIO/S3
  clients/core.py     REST-клиент core-service (резолв аудитории рассылок)
  errors.py           HTTP-исключения
  events.py           Kafka producer (aiokafka) + stub-режим
  main.py             сборка + lifespan
  models.py           реестр моделей для Alembic
  domains/
    accounts/         регистрация / профиль владельца ЛК
    applications/     подача и модерация заявок
    partners/         одобренный партнёр, логотип, события в Kafka
    staff/            кассиры: логин, JWT, CRUD
    broadcasts/       рассылки по сегментам аудитории
alembic/              миграции
```

## Аутентификация

- `X-Account-Id: <uuid>` — ручки владельца ЛК (`/accounts/me`, `/applications`,
  `/partners/me`, CRUD `/staff`).
- `X-Partner-Id: <uuid>` — партнёр-скоуп ЛК (`/broadcasts`); легаси-стаб, пока у ЛК нет своего JWT.
- `X-Admin-Id: <uuid>` — модераторские ручки (`/admin/*`).
- `Authorization: Bearer <jwt>` — кассир: JWT выдаётся на `POST /staff/login`
  (HS256, секрет `PARTNER_JWT_SECRET` ОБЯЗАН совпадать с `CORE_JWT_SECRET`,
  TTL `PARTNER_JWT_TTL_HOURS`). Этим токеном касса ходит в core-service.

Заголовки `X-*` — заглушка; реальный auth владельца/админа заменит только `app/deps.py`.

## Запуск

```bash
cp services/partner-service/.env.example services/partner-service/.env
cd services/partner-service
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8002
```

### API-документация

| | URL | |
|---|---|---|
| **Swagger UI** | `http://localhost:8002/docs` | интерактивная |
| **ReDoc** | `http://localhost:8002/redoc` | справка по схемам |
| **OpenAPI JSON** | `http://localhost:8002/openapi.json` | сырая спецификация |

### Переменные окружения (префикс `PARTNER_`)

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `PARTNER_DATABASE_URL` | `…@localhost:5432/tbank_loyalt` | DSN (psycopg, async) |
| `PARTNER_DB_SCHEMA` | `partner` | схема сервиса |
| `PARTNER_LOG_LEVEL` | `INFO` | уровень логирования |
| `PARTNER_CORE_BASE_URL` | `http://localhost:8001` | core-service для резолва аудитории |
| `PARTNER_JWT_SECRET` | dev-секрет | HS256 для JWT кассира (= `CORE_JWT_SECRET`) |
| `PARTNER_JWT_TTL_HOURS` | `12` | срок жизни JWT кассира |
| `PARTNER_KAFKA_ENABLED` | `false` | вкл/выкл публикацию в брокер |
| `PARTNER_KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | брокеры |
| `PARTNER_KAFKA_TOPIC_PARTNER_EVENTS` | `partner.events` | топик событий партнёра |
| `PARTNER_S3_ENDPOINT_URL` | `http://localhost:9000` | адрес MinIO для SDK |
| `PARTNER_S3_PUBLIC_URL` | `http://localhost:9000` | базовый URL для `logo_url` (видит браузер) |
| `PARTNER_S3_ACCESS_KEY` / `PARTNER_S3_SECRET_KEY` | `minioadmin` | креды MinIO |
| `PARTNER_S3_BUCKET` | `partner-logos` | бакет логотипов |
| `PARTNER_LOGO_MAX_BYTES` | `2 МБ` | лимит размера логотипа |

## Эндпоинты

| Группа | Ручки |
|---|---|
| `accounts` | `POST /accounts`, `GET /accounts/me`, `PATCH /accounts/me` |
| `applications` (партнёр) | `POST /applications`, `GET /applications/me`, `PATCH /applications/me/{id}`, `DELETE /applications/me` |
| `applications` (admin) | `GET /admin/applications`, `GET /admin/applications/{id}`, `POST /admin/applications/{id}/{approve,reject}` |
| `partners` (партнёр) | `GET /partners/me`, `PATCH /partners/me`, `PUT /partners/me/logo` |
| `partners` (admin) | `GET /admin/partners`, `GET /admin/partners/{id}`, `POST /admin/partners/{id}/{suspend,block,unblock}` |
| `staff` | `POST /staff/login`, `GET /staff/me` (по JWT), `GET /staff`, `POST /staff`, `PATCH /staff/{id}`, `DELETE /staff/{id}` |
| `broadcasts` | `GET /broadcasts`, `GET /broadcasts/audience`, `POST /broadcasts`, `GET /broadcasts/{id}`, `PATCH /broadcasts/{id}`, `DELETE /broadcasts/{id}`, `POST /broadcasts/{id}/send` |
| `meta` | `GET /health` |

## Kafka

Producer стартует в `lifespan`. Если `PARTNER_KAFKA_ENABLED=false` (по умолчанию),
события не публикуются в брокер, а просто логируются — работает локально без Kafka.
Каждое событие несёт сквозной `X-Request-ID`. Структура одинакова в обоих режимах:

```json
{
  "type": "partner.approved",
  "occurred_at": "2026-05-14T10:00:00+00:00",
  "payload": {
    "partner_id": "…", "account_id": "…", "application_id": "…",
    "name": "Кофе Хауз", "inn": "7707083893", "category": "food",
    "logo_url": null, "brand_color": null, "status": "active",
    "contact_email": "...", "contact_phone": "..."
  }
}
```

Типы событий (топик `partner.events`):

| Тип | Когда | Слушает |
|---|---|---|
| `partner.approved` | заявка одобрена, создан партнёр | core-service |
| `partner.updated` | партнёр изменил профиль/логотип | core-service |
| `partner.status_changed` | админ приостановил / заблокировал / разблокировал | core-service |
| `partner.broadcast` | партнёр отправил рассылку (с `customer_ids`) | notification-service |

## Сценарий онбординга (curl)

```bash
# 1. Регистрация аккаунта (получаем account_id)
ACC=$(curl -s localhost:8002/accounts -H 'content-type: application/json' \
  -d '{"email":"owner@cafe.ru","full_name":"Иван"}' | jq -r .id)

# 2. Подача заявки
APP=$(curl -s localhost:8002/applications -H "X-Account-Id: $ACC" \
  -H 'content-type: application/json' -d '{
    "business_name":"Кофе Хауз","inn":"7707083893","category":"food",
    "contact_email":"hello@cafe.ru"
  }' | jq -r .id)

# 3. Админ одобряет — создаётся partner + событие partner.approved
ADMIN=$(uuidgen | tr 'A-Z' 'a-z')
curl localhost:8002/admin/applications/$APP/approve \
  -H "X-Admin-Id: $ADMIN" -H 'content-type: application/json' -d '{}'

# 4. Партнёр редактирует профиль — событие partner.updated
curl -X PATCH localhost:8002/partners/me \
  -H "X-Account-Id: $ACC" -H 'content-type: application/json' \
  -d '{"brand_color":"#7BB661"}'

# 4b. Логотип в MinIO (PNG/JPEG/SVG/WebP, ≤ PARTNER_LOGO_MAX_BYTES) —
#     logo_url проставляется автоматически, событие partner.updated
curl -X PUT localhost:8002/partners/me/logo \
  -H "X-Account-Id: $ACC" \
  -F 'file=@logo.png;type=image/png'

# 5. Заводим кассира и логинимся (JWT для кассы core-service)
curl localhost:8002/staff -H "X-Account-Id: $ACC" \
  -H 'content-type: application/json' \
  -d '{"login":"cashier1","password":"secret","name":"Касса №1"}'
TOKEN=$(curl -s localhost:8002/staff/login -H 'content-type: application/json' \
  -d '{"login":"cashier1","password":"secret"}' | jq -r .access_token)

# 6. Админ блокирует — событие partner.status_changed
PARTNER_ID=$(curl -s localhost:8002/partners/me -H "X-Account-Id: $ACC" | jq -r .id)
curl -X POST localhost:8002/admin/partners/$PARTNER_ID/block \
  -H "X-Admin-Id: $ADMIN"
```

## TODO

- Реальная аутентификация владельца/админа (email/пароль + JWT либо OTP)
  вместо заголовков `X-Account-Id`/`X-Admin-Id`.
- Аналитика партнёра проксируется из core (`GET /partner/analytics`) — отдельной
  агрегации в partner-service нет.
