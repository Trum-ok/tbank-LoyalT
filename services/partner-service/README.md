# partner-service

ЛК партнёра: регистрация бизнеса, модерация, профиль одобренного партнёра.

## Доменная модель

- **account** — учётная запись пользователя ЛК (auth — заглушка через `X-Account-Id`).
- **application** — заявка на регистрацию бизнеса (`pending` → `approved` / `rejected`).
- **partner** — одобренный партнёр; источник истины. При одобрении заявки и обновлении
  профиля публикуется событие в Kafka (`partner.events`), на которое подпишется
  core-service и обновит свой снэпшот.

```
[account] 1—∞ [application] —approve→ [partner]
                                       │
                                       └─ partner.approved → Kafka
                                       └─ partner.updated  → Kafka
                                       └─ partner.status_changed → Kafka
```

## Структура

```
app/
  config.py           pydantic-settings, префикс PARTNER_
  database.py         async engine, Base
  deps.py             X-Account-Id / X-Admin-Id
  errors.py           HTTP-исключения
  events.py           Kafka producer (aiokafka) + stub-режим
  main.py             сборка + lifespan
  models.py           реестр моделей для Alembic
  domains/
    accounts/         регистрация / профиль пользователя ЛК
    applications/     подача и модерация заявок
    partners/         одобренный партнёр и события в Kafka
alembic/              миграции
```

## Аутентификация

- `X-Account-Id: <uuid>` — для ручек партнёра (`/accounts/me`, `/applications`, `/partners/me`)
- `X-Admin-Id: <uuid>` — для модераторских ручек (`/admin/*`)

Заглушка. Когда подключим реальный auth, поменяется только `app/deps.py`.

## Kafka

Producer стартует в `lifespan`. Если `PARTNER_KAFKA_ENABLED=false` (по умолчанию),
события не публикуются в брокер, а просто логируются — это позволяет работать
локально без поднятой Kafka. Структура события одинакова в обоих режимах:

```json
{
  "type": "partner.approved",
  "occurred_at": "2026-05-14T10:00:00+00:00",
  "payload": {
    "partner_id": "…",
    "account_id": "…",
    "application_id": "…",
    "name": "Кофе Хауз",
    "inn": "7707083893",
    "category": "food",
    "logo_url": null,
    "brand_color": null,
    "status": "active",
    "contact_email": "...",
    "contact_phone": "..."
  }
}
```

Типы событий:
- `partner.approved` — заявка одобрена, создан партнёр;
- `partner.updated` — партнёр изменил свой профиль;
- `partner.status_changed` — админ приостановил / заблокировал / разблокировал.

## Запуск

```bash
cp services/partner-service/.env.example services/partner-service/.env
cd services/partner-service
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8002
```

OpenAPI: `http://localhost:8002/docs`

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

# 4b. Партнёр загружает кастомный логотип в MinIO — событие partner.updated.
#     logo_url проставляется автоматически на публичную ссылку MinIO,
#     каталог клиента покажет аватар вместо инициалов.
curl -X PUT localhost:8002/partners/me/logo \
  -H "X-Account-Id: $ACC" \
  -F 'file=@logo.png;type=image/png'

# 5. Админ блокирует — событие partner.status_changed
PARTNER_ID=$(curl -s localhost:8002/partners/me -H "X-Account-Id: $ACC" | jq -r .id)
curl -X POST localhost:8002/admin/partners/$PARTNER_ID/block \
  -H "X-Admin-Id: $ADMIN"
```

## TODO

- Реальная аутентификация (email/пароль + JWT либо OTP).
- Несколько аккаунтов на одного партнёра (сотрудники ЛК).
- Аналитика (дашборд для партнёра) — требует доступа к данным core.
- Коммуникации (рассылки push-сегментам) — после notification-service.
