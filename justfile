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

# List recent tags (no args) or tag a release with notes (just release 1.2.3)
release version="":
    #!/usr/bin/env bash
    if [ -z "{{version}}" ]; then
        echo "Recent tags:"
        git tag --sort=-v:refname | head -10
    else
        LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
        echo "=== Recent tags ==="
        git tag --sort=-v:refname | head -5
        echo ""
        echo "=== Release notes for v{{version}} ==="
        if [ -n "$LAST_TAG" ]; then
            git log "${LAST_TAG}..HEAD" --oneline
        else
            git log --oneline -20
        fi
        echo ""
        echo "Tagging v{{version}} and pushing..."
        git tag v{{version}}
        git push origin v{{version}}
        echo "Done — CI will build and push the Docker image"
    fi
