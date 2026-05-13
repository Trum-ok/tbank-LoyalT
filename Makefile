.PHONY: all style ty lint deps

package?=app

all: deps

style:
	uv run python -m black $(package)
	uv run python -m isort $(package)
	uv run python -m ruff check $(package)

ty:
	uv run python -m ty check $(package)

lint: style ty

deps:
	uv sync


