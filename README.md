<h1><img src="app/static/images/dropit-logo.png" alt="dropit logo" height="60" style="vertical-align:middle;margin-right:12px"> drop•it</h1>

Self-hosted HTML file sharing. Upload an HTML file, get a short-lived public URL.

> **See it in action:** [this README is hosted on dropit](https://c81920cc.dropit.patilla.es/)

<p align="center">
  <img src="app/static/images/screenshot-index.png" alt="Landing page" width="48%">
  &nbsp;
  <img src="app/static/images/screenshot-admin.png" alt="Admin panel" width="48%">
</p>

## Quick start

```bash
cp .env.example .env        # set ADMIN_TOKEN and BASE_URL
just install                # create venv and install deps
just dev                    # run on http://localhost:8000
```

Then open `http://localhost:8000/admin`, sign in with your `ADMIN_TOKEN`, and create your first
user — you'll be shown their token once. Hand that token to the user (or use it yourself) on
`http://localhost:8000` to drop an HTML file and copy the link.

## Users & tokens

Users live in the database; a **token is the login** (no passwords). User management happens in
the admin panel:

- **Admins create users** — a 32-char token is generated and shown **once** on creation. It's
  stored hashed, so it can never be displayed again, only regenerated.
- **Admins can regenerate or delete any user.** Deleting a user keeps their already-uploaded pages.
- **Any user can regenerate their own token** from the main page ("regenerate" next to their name).

Regenerating a token immediately invalidates the old one **everywhere** (other browsers, devices,
and the CLI), so the new token must be re-pasted wherever it was used.

`ADMIN_TOKEN` is a permanent **break-glass admin login** used to bootstrap the first user and to
recover access. It is set via the environment (not managed in the DB) and cannot be regenerated
from the UI. Generate one with `just admin-token`. It also unlocks the `forever` TTL and bypasses
the per-user TTL limit.

> **Upgrading from a pre-database version?** This is a breaking change — `UPLOAD_TOKENS` is gone.
> Existing tokens are not migrated; recreate users from the admin panel after upgrading.

## Admin panel

Visit `http://localhost:8000/admin` and sign in with any admin token (the break-glass
`ADMIN_TOKEN` or a token belonging to a user marked as admin). From there you can manage users
(create, regenerate, delete), list and delete all uploaded pages, and run/inspect the cleanup
scheduler.

## Upload via API

```bash
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer tok_abc123" \
  -F "file=@page.html"
# {"url": "http://a3f8c1d2.localhost:8000", "expires_at": "..."}

# Custom TTL (1h, 6h, 24h, 48h, 7d — or "forever" with admin token)
curl -X POST "http://localhost:8000/upload?ttl=6h" \
  -H "Authorization: Bearer tok_abc123" \
  -F "file=@page.html"

# Permanent upload (admin token required)
curl -X POST "http://localhost:8000/upload?ttl=forever" \
  -H "Authorization: Bearer <admin-token>" \
  -F "file=@page.html"
```

## Claude Code integration

A [Claude Code skill](https://forgejo.patilla.es/patillacode/dotfiles/src/branch/main/dot_claude/skills/dropit/SKILL.md) is available for uploading HTML files directly from Claude Code sessions via `/dropit`. It handles file resolution, TTL selection, and upload in one step.

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
      # Sign in at /admin with this to create your users (no UPLOAD_TOKENS needed)
      ADMIN_TOKEN: your-admin-token-here
      # Your public URL
      BASE_URL: https://dropit.example.com
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

**Behind a reverse proxy** (nginx, Caddy, Traefik): remove the `ports` mapping, set `BASE_URL` to your public domain (e.g. `https://dropit.example.com`), set `CONTENT_DOMAIN` to the same domain (e.g. `dropit.example.com`), and proxy **both** `dropit.example.com` and `*.dropit.example.com` to the container on port 8000. You will need a wildcard SSL cert for `*.dropit.example.com` (Let's Encrypt DNS-01 challenge).

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
  -e BASE_URL=http://localhost:8000 \
  -e ADMIN_TOKEN=your-admin-token \
  -v $(pwd)/data:/data \
  dropit

# Or with compose (uses .env file)
docker compose up
```

## Development

```bash
just test           # run test suite
just lint           # check with ruff
just fix            # auto-fix lint + format
just reset-db       # delete dev database (forces fresh schema)
just admin-token    # generate a random admin token
```

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
| `BASE_URL` | `http://localhost:8000` | Base URL for the app (used in OpenAPI docs, health checks) |
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

Requires `REGISTRY_TOKEN` secret set in Forgejo.
