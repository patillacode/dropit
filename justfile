set dotenv-load

# List available recipes
default:
    @just --list

# Install dependencies
install:
    uv sync --all-extras

# Run dev server with hot reload on :8000
dev:
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

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

# Generate a random admin token
admin-token:
    @python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Delete dev database (forces fresh schema on next start)
reset-db:
    rm -f data/dropit.db
