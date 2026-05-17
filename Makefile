.PHONY: all style ty lint deps docker-build test

# Запускается из корня. Пути совпадают с .github/workflows/lint.yml,
# чтобы `make lint` локально давал тот же результат, что CI.
paths ?= services libs

SERVICES := core partner admin notification

all: deps

style:
	uv run python -m black $(paths)
	uv run python -m isort $(paths)
	uv run python -m ruff check $(paths)

ty:
	uv run python -m ty check libs/loyalt-common/src/loyalt_common
	@for s in $(SERVICES); do \
		echo "ty check services/$$s-service/app"; \
		uv run python -m ty check "services/$$s-service/app" || exit 1; \
	done

lint: style ty

deps:
	uv sync

# Локальный аналог job docker-build из CI: проверяем, что образ собирается.
docker-build:
	docker build -f deploy/Dockerfile -t tbank-loyalt:local .

# Локальный аналог job test из CI. Нужен Postgres на localhost:5433
# (см. tests/*/conftest.py) — например, из local/.
test:
	uv run pytest tests/core_service
	uv run pytest tests/partner_service
	uv run pytest tests/admin_service
	uv run pytest tests/notification_service
