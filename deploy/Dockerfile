FROM python:3.13-slim AS base

# Системные зависимости: curl нужен для HEALTHCHECK.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv — однофайловый бинарник, забираем готовый из официального образа.
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала ставим зависимости — это кешируемый слой, который перестраивается
# только при изменении pyproject.toml / uv.lock.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Затем код сервисов. Один образ — четыре сервиса; WORKDIR/CMD задаём в compose.
COPY services ./services

WORKDIR /app/services/core-service

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=10 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
