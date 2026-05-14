# core-service

Центральный сервис платформы лояльности. Отвечает за:

- программы лояльности и правила начисления (Накопительная / За визит / Штампы);
- каталог наград партнёров;
- начисление, списание и отмену баллов;
- историю транзакций;
- профиль клиента, баланс и список подключённых программ;
- публичный каталог программ для клиентов.

## Структура

```
app/
  config.py            настройки (pydantic-settings, префикс CORE_)
  database.py          async engine, Base, get_session
  deps.py              FastAPI зависимости (current_customer_id, current_partner_id)
  errors.py            HTTP-ошибки домена
  main.py              сборка приложения и подключение роутеров
  models.py            реестр всех моделей для Alembic
  domains/
    partners/          снэпшот партнёра (источник истины — partner-service)
    programs/          программы лояльности, переходы статусов
    rewards/           каталог наград
    catalog/           публичный каталог программ для клиентов
    enrollments/       подключение клиента к программе, профиль клиента
    points/            начисление/списание/отмена + баланс
    transactions/      история и выборки
alembic/               миграции
```

Каждый домен оформлен vertical slice: `models.py`, `schemas.py`, `service.py`, `router.py`.

## Аутентификация

Временно — заголовками от API Gateway (TODO: заменить на T-ID / JWT):

- `X-Customer-Id: <uuid>` — для клиентских ручек;
- `X-Partner-Id: <uuid>` — для партнёрских ручек.

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

OpenAPI: `http://localhost:8001/docs`

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

# 6. Партнёр начисляет баллы за покупку на 1200 ₽
curl localhost:8001/points/accrue \
  -H "X-Partner-Id: $PARTNER_ID" -H 'content-type: application/json' \
  -d "{\"customer_id\":\"$CUSTOMER_ID\",\"program_id\":\"$PROGRAM_ID\",
       \"purchase_amount\":\"1200.00\"}"

# 7. Клиент смотрит баланс
curl localhost:8001/balance/$PROGRAM_ID -H "X-Customer-Id: $CUSTOMER_ID"
```

## Модель данных

- **partner** — снэпшот партнёра.
- **program** — программа лояльности (`accrual_rule` в JSONB, статусы DRAFT → PUBLISHED → PAUSED/ARCHIVED).
- **reward** — награды для конкретной программы.
- **customer** — клиент (id = T-ID).
- **enrollment** — связь клиента и программы; денормализованный `points_balance`.
- **transaction** — операция (ACCRUAL / REDEMPTION / REVERSAL / EXPIRATION); баланс
  обновляется атомарно вместе с записью транзакции под `SELECT ... FOR UPDATE`
  на строке `enrollment`.

## TODO

- Сгорание баллов по `expires_at` (cron-job или Kafka-сигнал из таймера).
- Публикация Kafka-событий: `points.accrued`, `points.redeemed` —
  для `notification-service`.
- Реальная авторизация (T-ID/JWT) вместо заголовков `X-Customer-Id`/`X-Partner-Id`.
- Бонусные акции и геймификация (Streak, день рождения, реферальная программа).
- Идемпотентность операций начисления/списания (`Idempotency-Key`).
