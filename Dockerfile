FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/ app/

RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --gid 1000 --no-create-home appuser && \
    mkdir -p /data/pages && \
    chown -R appuser:appuser /app /data

LABEL org.opencontainers.image.source=https://forgejo.patilla.es/patillacode/dropit

USER appuser

ENV UV_NO_CACHE=1

EXPOSE 52031

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "52031"]
