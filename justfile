set dotenv-load

install:
    uv sync --all-extras

dev:
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 52031

test:
    uv run pytest

lint:
    uv run ruff check app/ tests/

fix:
    uv run ruff check --fix app/ tests/ && uv run ruff format app/ tests/

format-check:
    uv run ruff format --check app/ tests/
