# admin-service

Админ-панель Т-Банка: модерация, управление каталогом, метрики платформы.

Особенность сервиса — он не хранит у себя то, что уже живёт в core или
partner-service. Модерация — HTTP-прокси в partner-service; метрики —
read-only выборки по соседним схемам в той же БД.

## Структура

```
app/
  config.py             ADMIN_* префикс, URL соседних сервисов, имена чужих схем
  database.py
  deps.py               X-Admin-Id → AdminAccount (проверка в БД, is_active)
  errors.py             + UpstreamError для прокси-ошибок
  clients/
    partner.py          httpx.AsyncClient к partner-service
  main.py               сборка + lifespan (старт/стоп partner-client)
  models.py             admin / catalog модели (не метрики — те через SQL)
  domains/
    admins/             admin_account; bootstrap первого админа
    moderation/         прокси /moderation/applications, /moderation/partners
    catalog/            categories / featured partners / banners
    metrics/            read-only сырой SQL по core.* и partner.*
alembic/                собственная схема `admin`
```

## Bootstrap первого админа

Создать первого админа можно без заголовков (`X-Admin-Id`) — пока таблица
пуста. После этого все запросы (кроме `POST /admins` следующих и `/health`)
требуют валидный `X-Admin-Id` существующего активного админа.

```bash
# Первый
ADMIN=$(curl -s localhost:8004/admins -H 'content-type: application/json' \
  -d '{"email":"root@tbank","full_name":"Admin"}' | jq -r .id)

# Остальные ручки
curl localhost:8004/metrics/overview -H "X-Admin-Id: $ADMIN"
```

## Модерация (прокси)

Все ручки `/moderation/*` транзитом ходят в partner-service на
`http://localhost:8002` (см. `ADMIN_PARTNER_SERVICE_URL`), передавая
`X-Admin-Id` принципала. Ошибки upstream возвращаются как `502 Bad Gateway`
с пояснением.

```bash
# Очередь заявок
curl 'localhost:8004/moderation/applications?status=pending' -H "X-Admin-Id: $ADMIN"

# Одобрить
curl -X POST localhost:8004/moderation/applications/$APP_ID/approve \
  -H "X-Admin-Id: $ADMIN" -H 'content-type: application/json' \
  -d '{"comment":"OK"}'

# Заблокировать партнёра
curl -X POST localhost:8004/moderation/partners/$PARTNER_ID/block \
  -H "X-Admin-Id: $ADMIN"
```

## Метрики (read-only SQL по чужим схемам)

В предположении одна БД / разные схемы (см. CLAUDE.md). Имена схем
конфигурируемы (`ADMIN_CORE_SCHEMA`, `ADMIN_PARTNER_SCHEMA`).

| Эндпоинт | Источник |
|---|---|
| `GET /metrics/overview` | агрегация из всех ниже |
| `GET /metrics/partners` | `core.partner`, `partner.application` |
| `GET /metrics/customers` | `core.customer`, `core.enrollment` |
| `GET /metrics/transactions?days=N` | `core.transaction` (с фильтром по дате) |
| `GET /metrics/top-partners?limit=N&days=N` | `core.partner` + `core.transaction` |
| `GET /metrics/new-customers?days=N` | `core.customer` |
| `GET /metrics/new-partners?days=N` | `core.partner` |

## Каталог

Категории каталога остаются фиксированным enum'ом (food/beauty/retail/services/entertainment),
здесь хранятся **переопределения**: label, описание, порядок, активность.

- `PUT /catalog/categories/{code}` — upsert настроек категории.
- `POST /catalog/featured` / `DELETE /catalog/featured/{id}` — выделение партнёров.
- `POST /catalog/banners` / `PATCH /catalog/banners/{id}` / `DELETE …` — промо-баннеры.

## Запуск

```bash
cp services/admin-service/.env.example services/admin-service/.env
cd services/admin-service
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8004
```

## TODO

- Реальная аутентификация админов (SSO / JWT) вместо заголовка `X-Admin-Id`.
- core-service пока не публикует данные о клиентах партнёра — `top-partners`
  показывает только тех, у кого уже есть транзакции; для retention нужен
  отдельный домен в core.
- Кэширование метрик (Redis) — сейчас каждый запрос читает чужие таблицы заново.
- При запуске core-service в отдельной БД read-only-схемы придётся заменить
  на HTTP к core, либо подписаться на Kafka и собирать собственный read model.
- Категории каталога потом перенести в core / общую таблицу, чтобы клиент
  и admin-service видели одни и те же label'ы.
