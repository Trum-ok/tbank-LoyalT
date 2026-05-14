# notification-service

Push-уведомления для клиентов: реактивные сообщения о начислении/списании баллов,
сгорании, доступной награде, новых акциях.

На текущем этапе доставка — stub (запись в БД + лог); реальный провайдер
(FCM/APNs) подключается заменой `_deliver` в [notifications/service.py](app/domains/notifications/service.py).

## Структура

```
app/
  config.py           PARTNER_/CORE_/NOTIFICATION_ префикс, kafka_enabled и список топиков
  database.py
  deps.py             X-Customer-Id (заглушка)
  errors.py
  consumer.py         AIOKafkaConsumer + lifecycle
  main.py             FastAPI + lifespan (старт/стоп consumer)
  models.py           реестр для Alembic
  domains/
    devices/          регистрация device tokens (iOS/Android/Web)
    notifications/    модель, stub-delivery, история для клиента
    inbox/            handlers по типам событий + POST /internal/events для тестов
alembic/              миграции
```

## Аутентификация

`X-Customer-Id: <uuid>` — пока заглушка. Заменится на T-ID при подключении gateway.

## Поток событий

```
core-service / partner-service  ──events──▶  Kafka topics
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

Если `NOTIFICATION_KAFKA_ENABLED=false`, consumer не стартует. Для теста
можно дернуть событие напрямую через HTTP:

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

| Тип события | Источник | Результат |
|---|---|---|
| `points.accrued` | core | push «+N баллов · {partner}» |
| `points.redeemed` | core | push «Списано N баллов · {reward}» |
| `points.expiring` | core (cron) | push «N баллов сгорят через X дн.» |
| `reward.available` | core | push «Накопили на награду» |
| `partner.new_promotion` | partner | (логирование, fan-out — TODO) |
| `partner.approved` | partner | служебное (без push) |

## Запуск

```bash
cp services/notification-service/.env.example services/notification-service/.env
cd services/notification-service
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8003
```

OpenAPI: `http://localhost:8003/docs`

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
```

## TODO

- Cron на сгорание баллов в core (генерация `points.expiring`).
- Реальная отправка через FCM/APNs.
- Подписка клиента на партнёра для fan-out по `partner.new_promotion`.
- Массовые кампании от партнёров (POST /campaigns + сегментация).
- Идемпотентность обработки событий по `event_id` (сейчас Kafka гарантирует at-least-once).
