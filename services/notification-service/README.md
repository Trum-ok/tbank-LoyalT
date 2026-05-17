# notification-service

Push-уведомления для клиентов: сообщения о начислении/списании баллов, скором сгорании и сгорании баллов, рассылках
партнёра.

На текущем этапе доставка — stub (запись в БД + лог); реальный провайдер
(FCM/APNs) подключается заменой `_deliver` в [notifications/service.py](app/domains/notifications/service.py).

## Структура

```
app/
  config.py           pydantic-settings, префикс NOTIFICATION_ (kafka + список топиков)
  database.py
  deps.py             X-Customer-Id (заглушка)
  errors.py
  consumer.py         AIOKafkaConsumer + lifecycle
  main.py             FastAPI + lifespan (старт/стоп consumer)
  models.py           реестр для Alembic
  domains/
    devices/          регистрация/список/удаление device tokens (iOS/Android/Web)
    notifications/    модель, stub-delivery, история и отметка «прочитано»
    inbox/            handlers по типам событий + POST /internal/events для тестов
alembic/              миграции
```

## Аутентификация

`X-Customer-Id: <uuid>` — пока заглушка. Заменится на T-ID при подключении gateway.

## Поток событий

```
core-service / partner-service  ──events──▶  Kafka (core.events, partner.events)
                                                  │
                                                  ▼
                                       EventConsumer (lifespan)
                                                  │
                                                  ▼
                                       inbox.handle_event(type, payload)
                                                  │
                                                  ▼
                                       notifications.create_and_deliver
                                                  │
                                  ┌───────────────┴───────────────┐
                                  ▼                               ▼
                              запись в БД                   лог push'ей по
                          (история клиента)                 device tokens
```

Если `NOTIFICATION_KAFKA_ENABLED=false` (по умолчанию), consumer не стартует.
Для теста можно дёрнуть событие напрямую через HTTP:

```bash
curl localhost:8003/internal/events -H 'content-type: application/json' -d '{
  "type": "points.accrued",
  "payload": {
    "customer_id": "11111111-1111-1111-1111-111111111111",
    "points": 80,
    "partner_name": "Кофе Хауз"
  }
}'
```

## Поддерживаемые типы событий

| Тип события             | Источник            | Результат                                           |
|-------------------------|---------------------|-----------------------------------------------------|
| `points.accrued`        | core                | push «+N баллов · {partner}»                        |
| `points.redeemed`       | core                | push «Списано N баллов · {reward}»                  |
| `points.expiring`       | core (job сгорания) | push «N баллов сгорят через X дн.»                  |
| `points.expired`        | core (job сгорания) | push «N баллов сгорели · {partner}»                 |
| `reward.available`      | core                | push «Накопили на награду»                          |
| `partner.broadcast`     | partner             | фан-аут по `payload.customer_ids` (тип `broadcast`) |
| `partner.new_promotion` | partner             | только лог (fan-out — TODO, hook на будущее)        |
| `partner.approved`      | partner             | служебное (без push, только лог)                    |

## Запуск

```bash
cp services/notification-service/.env.example services/notification-service/.env
cd services/notification-service
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8003
```

### API-документация

|                  | URL                                  |                    |
|------------------|--------------------------------------|--------------------|
| **Swagger UI**   | `http://localhost:8003/docs`         | интерактивная      |
| **ReDoc**        | `http://localhost:8003/redoc`        | справка по схемам  |
| **OpenAPI JSON** | `http://localhost:8003/openapi.json` | сырая спецификация |

### Переменные окружения (префикс `NOTIFICATION_`)

| Переменная                             | По умолчанию                    | Назначение           |
|----------------------------------------|---------------------------------|----------------------|
| `NOTIFICATION_DATABASE_URL`            | `…@localhost:5432/tbank_loyalt` | DSN (psycopg, async) |
| `NOTIFICATION_DB_SCHEMA`               | `notification`                  | схема сервиса        |
| `NOTIFICATION_LOG_LEVEL`               | `INFO`                          | уровень логирования  |
| `NOTIFICATION_KAFKA_ENABLED`           | `false`                         | вкл/выкл consumer    |
| `NOTIFICATION_KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092`                | брокеры              |
| `NOTIFICATION_KAFKA_GROUP_ID`          | `notification-service`          | consumer group       |
| `NOTIFICATION_KAFKA_TOPICS`            | `[core.events, partner.events]` | топики consumer'а    |

## Эндпоинты

| Группа          | Ручки                                                              |
|-----------------|--------------------------------------------------------------------|
| `devices`       | `POST /devices`, `GET /devices`, `DELETE /devices/{device_id}`     |
| `notifications` | `GET /notifications`, `POST /notifications/{notification_id}/read` |
| `internal`      | `POST /internal/events`                                            |
| `meta`          | `GET /health`                                                      |

## Модель данных

- **device** — токен устройства клиента; `platform` ∈ {ios, android, web}.
- **notification** — `customer_id`, `type` (`NotificationType`), `title`/`body`,
  `payload` (JSON), `delivery_status` ∈ {pending, sent, failed, skipped},
  `delivered_at`, `delivery_error`, `is_read`. `skipped` — у клиента нет активных
  устройств.

## Сценарий (curl)

```bash
CUSTOMER=11111111-1111-1111-1111-111111111111

# 1. Клиент регистрирует устройство
curl localhost:8003/devices -H "X-Customer-Id: $CUSTOMER" \
  -H 'content-type: application/json' \
  -d '{"token":"fcm_aaaaaa_demo_token","platform":"android"}'

# 2. Эмулируем событие из core
curl localhost:8003/internal/events -H 'content-type: application/json' -d "{
  \"type\":\"points.accrued\",
  \"payload\":{\"customer_id\":\"$CUSTOMER\",\"points\":80,\"partner_name\":\"Кофе Хауз\"}
}"

# 3. Клиент видит уведомление в истории
curl localhost:8003/notifications -H "X-Customer-Id: $CUSTOMER"

# 4. Отмечает прочитанным
NID=$(curl -s localhost:8003/notifications -H "X-Customer-Id: $CUSTOMER" | jq -r '.[0].id')
curl -X POST localhost:8003/notifications/$NID/read -H "X-Customer-Id: $CUSTOMER"
```

## TODO

- Реальная отправка через FCM/APNs (сейчас `_deliver` — stub).
- Fan-out по `partner.new_promotion` (подписка клиента на партнёра) — пока только лог.
- Идемпотентность обработки событий по `event_id` (Kafka даёт at-least-once).
