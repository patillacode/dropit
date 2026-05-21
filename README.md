# dropit

Self-hosted HTML file sharing. Upload an HTML file, get a short-lived public URL.

## Local dev

```bash
cp .env.example .env        # edit UPLOAD_TOKENS and BASE_URL
just install                # create venv and install deps
just dev                    # run on http://localhost:52031
```

## Upload a file

```bash
curl -X POST http://localhost:52031/upload \
  -H "Authorization: Bearer tok_abc123" \
  -F "file=@page.html"
# {"url": "http://localhost:52031/p/a3f8c1d2", "expires_at": "..."}

# with custom TTL (1h, 6h, 24h, 48h, 7d)
curl -X POST "http://localhost:52031/upload?ttl=6h" \
  -H "Authorization: Bearer tok_abc123" \
  -F "file=@page.html"
```

## Docker

```bash
# build
docker build -t dropit .

# run
docker run -p 52031:52031 \
  -e UPLOAD_TOKENS=alice:tok_abc123 \
  -e BASE_URL=http://localhost:52031 \
  -v $(pwd)/data:/data \
  dropit

# or with compose (uses .env file)
docker compose up
```

## Tests

```bash
just test
just lint
just fix        # auto-fix lint + format
```

## Configuration

All settings via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `UPLOAD_TOKENS` | required | `name:token` pairs, comma-separated |
| `ALLOWED_TTLS` | `1h,6h,24h,48h,7d` | Accepted TTL values |
| `DEFAULT_TTL` | `24h` | TTL when not specified |
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
