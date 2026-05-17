# LoyalT — платформа лояльности | LLM Chads <img src="docs/assets/chad.webp" alt="chad" height="25" valign="middle">

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-schema--per--service-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Apache%20Kafka-events-231F20?logo=apachekafka&logoColor=white" alt="Kafka">
  <img src="https://img.shields.io/badge/Angular-signals-DD0031?logo=angular&logoColor=white" alt="Angular">
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/Taiga%20UI-bank%20kit-FFDD2D" alt="Taiga UI">
  <img src="https://img.shields.io/badge/Docker-compose-2496ED?logo=docker&logoColor=white" alt="Docker">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-D97757" alt="License: MIT"></a>
</p>

**LoyalT** — встраиваемая в приложение Т-Банка (клиентская часть в раздел «Город») платформа лояльности.

Полный перечень возможностей: [docs/functional_requirements.md](docs/functional_requirements.md).

https://github.com/user-attachments/assets/322bd190-22e0-4806-8f7c-baabbadd6eb4

---

## Архитектура

Набор микросервисов, каждый — отдельное FastAPI-приложение со своей зоной
ответственности и своей схемой в общем PostgreSQL (schema-per-service).
Синхронная связь — REST по внутренней сети, асинхронная — через Kafka
(начисление баллов → push и т. п. идут событиями, не блокирующими вызовами).

Диаграмма потоков событий и сценарий end-to-end — в [deploy/README.md](deploy/README.md).

### Бэкенд

Python 3.13, FastAPI (полностью `async`), SQLAlchemy + `psycopg`, Alembic
(вся схема — только через миграции). Миграции прогоняет отдельный one-shot
сервис `migrate` (`alembic upgrade head` по всем схемам) до старта сервисов;
остальные ждут его через `depends_on: service_completed_successfully`.

| Сервис                 | Что делает                                                                                                                                             | Порт | Расположение                                                   | Тех-док                                           |
|------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|------|----------------------------------------------------------------|---------------------------------------------------|
| `core-service`         | Программы лояльности и правила начисления, каталог наград, начисление/списание баллов, история транзакций, отмена, профиль и баланс клиента, аналитика | 8001 | [services/core-service](services/core-service)                 | [README](services/core-service/README.md)         |
| `partner-service`      | ЛК партнёра: регистрация бизнеса, заявка на модерацию, профиль одобренного партнёра, собственная авторизация                                           | 8002 | [services/partner-service](services/partner-service)           | [README](services/partner-service/README.md)      |
| `notification-service` | Push-уведомления: начисление баллов, доступная награда, сгорание баллов, новые акции                                                                   | 8003 | [services/notification-service](services/notification-service) | [README](services/notification-service/README.md) |
| `admin-service`        | Панель Т-Банка: модерация заявок (прокси в `partner-service`), управление каталогом, метрики платформы (read-only в чужие схемы)                       | 8004 | [services/admin-service](services/admin-service)               | [README](services/admin-service/README.md)        |

Внутри каждого сервиса код нарезан по доменам в стиле **vertical slice** —
каждый домен самодостаточен: `models.py`, `schemas.py`, `service.py`, `router.py`. Общий код сервисов — в [libs/](libs).

### Фронтенд

**TypeScript** + **Angular** на [**Taiga UI**](https://github.com/taiga-family/taiga-ui) — банковском UI-ките Т-Банка.
Все
приложения — pnpm-workspace под `frontend/`.

| Приложение | Для кого                                                                                    | Расположение                           |
|------------|---------------------------------------------------------------------------------------------|----------------------------------------|
| `customer` | Клиент: программы, баланс, история, QR на кассе, каталог — экран «как в приложении Т-Банка» | [frontend/customer](frontend/customer) |
| `partner`  | Бизнес: no-code конструктор программы, награды, акции, рассылки, дашборд и аналитика        | [frontend/partner](frontend/partner)   |
| `cashier`  | Касса/официант: сканирование QR клиента, начисление и списание баллов                       | [frontend/cashier](frontend/cashier)   |
| `admin`    | Т-Банк: очередь модерации, каталог, метрики платформы                                       | [frontend/admin](frontend/admin)       |
| `shared`   | Общий пакет (`@tbank-loyalt/shared`): UI, API-клиенты, типы                                 | [frontend/shared](frontend/shared)     |

### CI/CD

<p>
  <a href="https://github.com/Trum-ok/tbank-loyalt/actions/workflows/lint.yml"><img src="https://github.com/Trum-ok/tbank-loyalt/actions/workflows/lint.yml/badge.svg" alt="lint"></a>
  <a href="https://github.com/Trum-ok/tbank-loyalt/actions/workflows/test.yml"><img src="https://github.com/Trum-ok/tbank-loyalt/actions/workflows/test.yml/badge.svg" alt="test"></a>
  <a href="https://github.com/Trum-ok/tbank-loyalt/actions/workflows/docker-build.yml"><img src="https://github.com/Trum-ok/tbank-loyalt/actions/workflows/docker-build.yml/badge.svg" alt="docker-build"></a>
</p>

Три независимых workflow в GitHub Actions на каждый `push` и `pull_request`:

- `lint` - black + isort + ruff + ty;
- `test` - pytest по бэку с сервис-контейнером PostgreSQL;
- `docker-build` - проверка, что Docker-образ собирается.

## API-документация

После запуска документация доступна автоматически:

|                  | URL                                          |
|------------------|----------------------------------------------|
| **Swagger UI**   | `http://localhost:SERVICE_PORT/docs`         |
| **ReDoc**        | `http://localhost:SERVICE_PORT/redoc`        |
| **OpenAPI JSON** | `http://localhost:SERVICE_PORT/openapi.json` |

---

## Запуск

### Весь стек одной командой (Docker)

Поднимает PostgreSQL, Kafka и все четыре сервиса с автоматическими миграциями.

```bash
cd deploy
docker compose up --build      # первый запуск ~3–5 мин (сборка образа)
```

Сервисы будут на `localhost:8001–8004`. Подробности, отладка Kafka и
готовый end-to-end сценарий (создать админа → заявку → программу →
начислить баллы → увидеть push) — в [deploy/README.md](deploy/README.md).

### Фронтенд

```bash
pnpm install

pnpm customer   # клиентское приложение
pnpm partner    # ЛК партнёра
pnpm cashier    # касса
pnpm admin      # админка Т-Банка
```

### Разработка бэкенда

Зависимости управляются через `uv`; типовые задачи — в `Makefile`:

```bash
make deps                          # uv sync
make lint                          # black + isort + ruff + ty
uv run uvicorn app.main:app --reload   # один сервис локально
```

Для итеративной разработки удобно держать в compose только `postgres` +
`kafka`, а нужный сервис гонять локально с `--reload`.

---

## Best Practice

*асинхронность · микросервисы · schema-per-service · vertical slice по доменам · Alembic-миграции (нет ручных DDL) ·
единый API Gateway + s2s REST/Kafka · Kafka со stub-режимом и /internal/events для локалки · идемпотентные
обработчики событий и джобы · сквозной X-Request-ID через HTTP и Kafka · структурное JSON-логирование · общий пакет
loyalt-common (DRY) · единый контракт ошибок {"detail": …} + типобезопасные OpenAPI-ответы · богатый Swagger/ReDoc ·
JWT (HS256) · запросы в транзакциях · HASH-партиционирование горячей таблицы транзакций · read-реплика для тяжёлых
выборок · тюнингуемый пул соединений · линт-гейт (black/isort/ruff/ty) + pytest с PostgreSQL-контейнером + проверка
сборки Docker в CI · one-shot migrate-сервис.*

Вроде все написали...

## Команда LLM Chads

- **Артамонов Аркадий**     ([@OpSonata](https://t.me/OpSonata))
- **Маркин Антон**          ([@drhnam](https://t.me/drhnam))
- <a href="https://claude.com/claude-code"><img src="docs/assets/clawd.png" alt="Claw'd" height="22" valign="middle"></a>

## Лицензия

[MIT](LICENSE)
