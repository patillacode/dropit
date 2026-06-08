# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
cp .env.example .env  # first-time setup — set ADMIN_TOKEN before running
just install        # create venv and install all deps (uv sync --all-extras)
just dev            # run dev server with hot reload on :8000
just test           # run test suite
just test-cov       # run tests with coverage — must reach 100%
just lint           # ruff check
just fix            # ruff check --fix + ruff format
just reset-db       # delete dev database
just admin-token    # generate a random admin token
```

Run a single test file: `uv run pytest tests/test_upload.py`
Run a specific test: `uv run pytest tests/test_upload.py::test_name`

## Architecture

dropit is a FastAPI app that lets users upload HTML files and serve each one at a unique subdomain (`{page_id}.{CONTENT_DOMAIN}`). It uses SQLite (WAL mode) via SQLModel, APScheduler for cleanup, structlog for structured logging, and slowapi for rate limiting.

### Request routing

Two middleware layers run before routers:

1. **`content_subdomain_middleware`** — intercepts any request where the host is `*.{CONTENT_DOMAIN}`. Extracts the page ID from the subdomain and calls `serve_page_content()` directly, bypassing all routers. This is how uploaded pages are served.
2. **`request_id_middleware`** — attaches a short UUID to every request via structlog contextvars.

All other requests fall through to the standard routers: `landing`, `config`, `health`, `me`, `upload`, `admin`, `users`.

### Auth

`app/auth.py` provides three FastAPI dependencies:
- `get_current_user` — resolves `Bearer` token to a `TokenUser` (checks env `ADMIN_TOKEN` first via constant-time compare, then DB lookup by SHA-256 hash)
- `verify_token` — wraps `get_current_user`, just returns the username
- `require_admin` — raises 403 if user is not admin

`ADMIN_TOKEN` is a break-glass env var (never stored in DB). It also bypasses `MAX_USER_TTL` and enables `forever` TTL.

### Models

Three SQLModel tables in `app/models.py`:
- `User` — name, hashed token, is_admin flag
- `Page` — 8-char ID, optional `expires_at`, `token_hint` (uploader hint), filename, file_size
- `CleanupRun` — audit log of each cleanup execution

### Database migrations

`app/database.py` implements manual SQLite migrations. `init_db()` runs `_run_migrations()` first, then `SQLModel.metadata.create_all()`. Migrations are tracked in a `schema_version` table; each migration function is idempotent. New migrations go in `_MIGRATIONS` list — the index determines order.

### Settings

`app/settings.py` uses pydantic-settings. All config is env-var driven; `get_settings()` is cached with `@lru_cache`. The `.env` file is loaded automatically by `just` (via `set dotenv-load`).

## Testing

Tests use `pytest-asyncio` (`asyncio_mode = "auto"`) with an in-memory SQLite DB wired up in `tests/conftest.py`. **100% coverage is required** — `just test-cov` enforces this with `--cov-fail-under=100`.

The `client` fixture passes a pre-built in-memory engine to `create_app(engine=engine)`. The lifespan closes over it, so the scheduler and `app.state.engine` both use the test DB — no module-level patching needed.

**Settings cache**: `get_settings()` is `@lru_cache`'d. Call `get_settings.cache_clear()` after any `monkeypatch.setenv()` call, or the patched env vars won't take effect. Both `set_env` and `client` fixtures already do this.

The `todo/` directory is gitignored — never stage files from it.
