# dropit

Self-hosted HTML file sharing. Upload an HTML file, get a short-lived public URL.

## Quick start

```bash
cp .env.example .env        # edit UPLOAD_TOKENS and BASE_URL
just install                # create venv and install deps
just dev                    # run on http://localhost:8000
```

Open `http://localhost:8000` — enter your API token, drop an HTML file, copy the link.

## Admin panel

Visit `http://localhost:8000/admin` with your admin token to list and delete all uploaded pages.

Set `ADMIN_TOKEN` in your `.env` to enable it:
```bash
# Generate a secure token
just admin-token

# Add to .env
ADMIN_TOKEN=<generated-value>
```

The admin token also unlocks the `forever` TTL and bypasses the per-user TTL limit.

## Upload via API

```bash
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer tok_abc123" \
  -F "file=@page.html"
# {"url": "http://localhost:8000/p/a3f8c1d2", "expires_at": "..."}

# Custom TTL (1h, 6h, 24h, 48h, 7d — or "forever" with admin token)
curl -X POST "http://localhost:8000/upload?ttl=6h" \
  -H "Authorization: Bearer tok_abc123" \
  -F "file=@page.html"

# Permanent upload (admin token required)
curl -X POST "http://localhost:8000/upload?ttl=forever" \
  -H "Authorization: Bearer <admin-token>" \
  -F "file=@page.html"
```

## Docker

```bash
# Build
docker build -t dropit .

# Run
docker run -p 8000:8000 \
  -e UPLOAD_TOKENS=alice:tok_abc123 \
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
| `UPLOAD_TOKENS` | required | `name:token` pairs, comma-separated |
| `ADMIN_TOKEN` | — | Token for `/admin` panel; also allows `forever` TTL and bypasses `MAX_USER_TTL` |
| `ALLOWED_TTLS` | `1h,6h,24h,48h,7d` | Accepted TTL values; add `forever` to enable permanent uploads |
| `DEFAULT_TTL` | `24h` | TTL when not specified in upload request |
| `MAX_USER_TTL` | `24h` | Maximum TTL for non-admin tokens |
| `MAX_UPLOAD_SIZE` | `5242880` | Max upload size in bytes (5 MB) |
| `CLEANUP_INTERVAL_HOURS` | `1` | How often expired pages are purged |
| `DATA_DIR` | `./data` | Directory for SQLite DB and uploaded files |
| `BASE_URL` | `http://localhost:52031` | Base URL for generated share links |

## Release

Tag a version to trigger Docker build and push:

```bash
git tag v0.1.0
git push --tags
```

Requires `REGISTRY_TOKEN` secret set in Forgejo.
