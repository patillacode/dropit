<h1><img src="app/static/images/dropit-logo.png" alt="dropit logo" height="60" style="vertical-align:middle;margin-right:12px"> drop•it</h1>

Drop an HTML file. Get a link.

> **Live demo:** [the dropit feature page, served by dropit itself](https://c81920cc.dropit.patilla.es/)

<p align="center">
  <img src="app/static/images/screenshot-index.png" alt="Landing page" width="48%">
  &nbsp;
  <img src="app/static/images/screenshot-admin.png" alt="Admin panel" width="48%">
</p>

## Quick start

```bash
cp .env.example .env        # set ADMIN_TOKEN
just install                # venv + deps, install prek, set up git hooks
just dev                    # run on http://localhost:8000
```

`just install` syncs Python deps, installs [prek](https://prek.j178.dev/) (via `uv tool
install`) and sets up the git hooks. Linting/formatting of JS & CSS uses
[Biome](https://biomejs.dev/), fetched on demand via `npx`, so **Node is required** for the
`*-web` recipes locally (CI installs the Biome standalone binary instead).

1. Open `http://localhost:8000/admin` and sign in with your `ADMIN_TOKEN`
2. Create a user — their token is shown once, copy it
3. Go to `http://localhost:8000`, paste the token, drop an HTML file, copy the link

## Users & tokens

Users live in the database; a **token is the login** (no passwords). User management happens in
the admin panel:

- **Admins create users** — a 32-char token is generated and shown **once** on creation. It's
  stored hashed, so it can never be displayed again, only regenerated.
- **Admins can regenerate or delete any user.** Deleting a user permanently removes all their pages and collections.
- **Any user can regenerate their own token** from the main page ("regenerate" next to their name).

Regenerating a token immediately invalidates the old one **everywhere** (other browsers, devices,
and the CLI), so the new token must be re-pasted wherever it was used.

`ADMIN_TOKEN` is a permanent **break-glass admin login** used to bootstrap the first user and to
recover access. It is set via the environment (not managed in the DB) and cannot be regenerated
from the UI. Generate one with `just admin-token`. It also unlocks the `forever` TTL and bypasses
the per-user TTL limit.

## Admin panel

Visit `http://localhost:8000/admin` and sign in with any admin token (the break-glass
`ADMIN_TOKEN` or a token belonging to a user marked as admin). The overview card shows a live
count of users, pages, permanent uploads, and total storage. From there you can manage users
(create, regenerate, delete), list and delete all uploaded pages (with uploader and file details),
and run/inspect the cleanup scheduler.

## Collections

Pages can be grouped into **collections** — private labels visible only to the owner, never included in share URLs.

```bash
# Upload into a collection (auto-created on first use)
curl -X POST "http://localhost:8000/upload?collection=work" \
  -H "Authorization: Bearer tok_abc123" \
  -F "file=@page.html"
# {"url": "...", "collection": "work", ...}

# List your collections (with page counts)
curl http://localhost:8000/collections \
  -H "Authorization: Bearer tok_abc123"

# Filter your upload history by collection
curl "http://localhost:8000/me/pages?collection=work" \
  -H "Authorization: Bearer tok_abc123"

# See only uncollected pages
curl "http://localhost:8000/me/pages?uncollected=true" \
  -H "Authorization: Bearer tok_abc123"
```

Collection names are normalized to lowercase. A collection is created automatically the first time you upload with a new name — no separate setup step required.

## Upload via API

```bash
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer tok_abc123" \
  -F "file=@page.html"
# {"url": "http://a3f8c1d2.localhost:8000", "expires_at": "...", "collection": null}

# Custom TTL (1h, 6h, 24h, 48h, 7d — or "forever" with admin token)
curl -X POST "http://localhost:8000/upload?ttl=6h" \
  -H "Authorization: Bearer tok_abc123" \
  -F "file=@page.html"

# Permanent upload (admin token required)
curl -X POST "http://localhost:8000/upload?ttl=forever" \
  -H "Authorization: Bearer <admin-token>" \
  -F "file=@page.html"
```

API endpoints are rate-limited per IP: `/upload` and `/me` at 5 requests/minute, `/me/regenerate` at 2 requests/minute. Exceeding the limit returns HTTP 429 with a `Retry-After` header.

## Claude Code integration

A [Claude Code skill](https://forgejo.patilla.es/patillacode/dotfiles/src/branch/main/dot_claude/skills/dropit/SKILL.md) is available for uploading HTML files directly from Claude Code sessions via `/dropit`. It handles file resolution, TTL selection, collection assignment, and upload in one step.

## Self-hosting

Pre-built images are published for **amd64** and **arm64** (Raspberry Pi 4/5):

| Registry | Image |
|---|---|
| GitHub (GHCR) | `ghcr.io/patillacode/dropit:latest` |
| Forgejo | `forgejo.patilla.es/patillacode/dropit:latest` |

Create a `compose.yml` on your server:

```yaml
services:
  dropit:
    image: ghcr.io/patillacode/dropit:latest
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data
    environment:
      # Break-glass admin token — generate with: openssl rand -hex 32
      # Sign in at /admin with this to create your users
      ADMIN_TOKEN: your-admin-token-here
      # Domain used for per-page share links (each page gets its own subdomain)
      # Requires a wildcard DNS record and SSL cert for *.dropit.example.com
      CONTENT_DOMAIN: dropit.example.com
      # Optional: allow permanent uploads (admin only)
      # ALLOWED_TTLS: 1h,6h,24h,48h,7d,forever
    restart: unless-stopped
```

```bash
docker compose up -d
```

Open `http://your-server-ip:8000`.

**Behind a reverse proxy** (nginx, Caddy, Traefik): remove the `ports` mapping, set `CONTENT_DOMAIN` to your public domain (e.g. `dropit.example.com`), and proxy **both** `dropit.example.com` and `*.dropit.example.com` to the container on port 8000. You will need a wildcard SSL cert for `*.dropit.example.com` (Let's Encrypt DNS-01 challenge).

**To update:**

```bash
docker compose pull && docker compose up -d
```

## Docker (local build)

```bash
# Build
docker build -t dropit .

# Run
docker run -p 8000:8000 \
  -e ADMIN_TOKEN=your-admin-token \
  -v $(pwd)/data:/data \
  dropit

# Or with compose (uses .env file)
docker compose up
```

## Development

```bash
just test           # run test suite
just lint           # check Python with ruff
just fix            # auto-fix lint + format (Python)
just lint-web       # lint + format-check JS/CSS with Biome
just format-web     # auto-format + safe-fix JS/CSS with Biome
just reset-db       # delete dev database (forces fresh schema)
just admin-token    # generate a random admin token
```

### Git hooks

`just install` sets up the [prek](https://prek.j178.dev/) git hooks (a fast drop-in for
pre-commit). If you need to (re)install them manually, run `just hooks`.

On every commit the hooks run ruff (lint + format), Biome (JS/CSS), and file-hygiene checks —
no tests, so commits stay fast. The test suite and 100% coverage gate run in CI. JS/CSS tooling
is pinned in `biome.json`; CI runs it as a separate `web` job.

## Configuration

All settings via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `ADMIN_TOKEN` | — | Break-glass admin login used to bootstrap users via `/admin`; also allows `forever` TTL and bypasses `MAX_USER_TTL`. All other users are created in the admin panel, not via env. |
| `ALLOWED_TTLS` | `1h,6h,24h,48h,7d` | Accepted TTL values; add `forever` to enable permanent uploads |
| `DEFAULT_TTL` | `24h` | TTL when not specified in upload request |
| `MAX_USER_TTL` | `24h` | Maximum TTL for non-admin tokens |
| `MAX_UPLOAD_SIZE` | `5242880` | Max upload size in bytes (5 MB) |
| `CLEANUP_INTERVAL_HOURS` | `1` | How often expired pages are purged |
| `DATA_DIR` | `./data` | Directory for SQLite DB and uploaded files |
| `CONTENT_DOMAIN` | `localhost:8000` | Domain for per-page share links — each page is served at `{id}.{CONTENT_DOMAIN}`; requires wildcard DNS + SSL in production |

## Cleanup

Expired pages are purged automatically by a background scheduler running inside the FastAPI process (APScheduler). On each run it deletes all pages whose `expires_at` has passed, removes the corresponding files from disk, and records the result.

The interval is controlled by `CLEANUP_INTERVAL_HOURS` (default: `1`). No cron job or external worker is needed.

The admin panel shows a **Cleanup scheduler** card with the last run timestamp, how many pages were deleted, whether it was triggered by the scheduler or manually, and the next scheduled run time. You can also trigger a cleanup immediately from the panel without waiting for the next interval.

## Release

Tag a version to trigger Docker build and push:

```bash
git tag v0.1.0
git push --tags
```

Requires two secrets set in Forgejo: `REGISTRY_TOKEN` (Forgejo registry) and `GHCR_TOKEN` (GitHub Container Registry).
