set dotenv-load

# List available recipes
default:
    @just --list

# Install dependencies
install:
    uv sync --all-extras

# Run dev server with hot reload on :52031
dev:
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 52031

# Run tests
test:
    uv run pytest

# Lint with ruff
lint:
    uv run ruff check app/ tests/

# Auto-fix lint and format issues
fix:
    uv run ruff check --fix app/ tests/ && uv run ruff format app/ tests/

# Check formatting (CI-safe, no writes)
format-check:
    uv run ruff format --check app/ tests/
