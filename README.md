# LoyalT — платформа лояльности

> Команда **LLM Chads**. Решение кейса LoyalT.

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

**LoyalT** — встраиваемая в приложение Т-Банка (раздел «Город») платформа лояльности.
Малый бизнес за пару минут собирает программу вознаграждений без кода, анализирует
поведение клиентов и удерживает их; клиенты копят и тратят баллы через **T-ID** —
без отдельных приложений, карт и регистраций.

## Зачем это нужно

- Удержание клиента — ключевая задача любого бизнеса, но механик лояльности немного и они повторяются.
- Малый бизнес вынужден строить системы лояльности сам или интегрировать тяжёлые сторонние решения (Stamp, Loyverse) с отдельным приложением.
- LoyalT даёт бесшовный, нативный для банковской экосистемы опыт: бизнес — в ЛК, клиент — внутри уже установленного приложения Т-Банка.

Полный перечень возможностей: [docs/functional_requirements.md](docs/functional_requirements.md).

---

## Архитектура

Набор микросервисов, каждый — отдельное FastAPI-приложение со своей зоной
ответственности и своей схемой в общем PostgreSQL (schema-per-service).
Синхронная связь — REST по внутренней сети, асинхронная — через Kafka
(начисление баллов → push и т. п. идут событиями, не блокирующими вызовами).

Диаграмма потоков событий и сценарий end-to-end — в [deploy/README.md](deploy/README.md).

### Бэкенд

Python 3.13, FastAPI (полностью `async`), SQLAlchemy + `psycopg`, Alembic
(вся схема — только через миграции). Каждый сервис на старте сам накатывает
`alembic upgrade head`.

| Сервис | Что делает | Порт | Расположение | Тех-док |
|---|---|---|---|---|
| `core-service` | Программы лояльности и правила начисления, каталог наград, начисление/списание баллов, история транзакций, отмена, профиль и баланс клиента, аналитика | 8001 | [services/core-service](services/core-service) | [README](services/core-service/README.md) |
| `partner-service` | ЛК партнёра: регистрация бизнеса, заявка на модерацию, профиль одобренного партнёра, собственная авторизация | 8002 | [services/partner-service](services/partner-service) | [README](services/partner-service/README.md) |
| `notification-service` | Push-уведомления: начисление баллов, доступная награда, сгорание баллов, новые акции | 8003 | [services/notification-service](services/notification-service) | [README](services/notification-service/README.md) |
| `admin-service` | Панель Т-Банка: модерация заявок (прокси в `partner-service`), управление каталогом, метрики платформы (read-only в чужие схемы) | 8004 | [services/admin-service](services/admin-service) | [README](services/admin-service/README.md) |

Общий код сервисов — в [libs/](libs).

### Фронтенд

TypeScript + Angular (standalone-компоненты, signals, esbuild) на **Taiga UI** —
банковском UI-ките Т-Банка. Все приложения — pnpm-workspace под `frontend/`.

| Приложение | Для кого | Расположение |
|---|---|---|
| `customer` | Клиент: программы, баланс, история, QR на кассе, каталог — экран «как в приложении Т-Банка» | [frontend/customer](frontend/customer) |
| `partner` | Бизнес: no-code конструктор программы, награды, акции, рассылки, дашборд и аналитика | [frontend/partner](frontend/partner) |
| `cashier` | Касса/официант: сканирование QR клиента, начисление и списание баллов | [frontend/cashier](frontend/cashier) |
| `admin` | Т-Банк: очередь модерации, каталог, метрики платформы | [frontend/admin](frontend/admin) |
| `shared` | Общий пакет (`@tbank-loyalt/shared`): UI, API-клиенты, типы | [frontend/shared](frontend/shared) |

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

## Команда LLM Chads

- **Артамонов Аркадий**     ([@OpSonata](https://t.me/OpSonata))
- **Маркин Антон**          ([@drhnam](https://t.me/drhnam))
- <a href="https://claude.com/claude-code"><img src="docs/assets/clawd.png" alt="Claw'd" height="22" valign="middle"></a>

## Лицензия

[MIT](LICENSE)
