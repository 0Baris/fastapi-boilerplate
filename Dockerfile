FROM python:3.13-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN /uv sync --frozen --no-install-project --no-dev

FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 PYTHONFAULTHANDLER=1

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl tini && rm -rf /var/lib/apt/lists/*

RUN groupadd -r app && useradd -r -g app app

COPY --from=builder --chown=app:app /app/.venv /app/.venv

COPY --chown=app:app . .

RUN chmod +x /app/start.sh /app/start-worker.sh /app/start-beat.sh /app/start-migrate.sh

USER app

# PORT is honored by all entrypoints; HEALTHCHECK_PATH is overridable per service
# (worker/beat wrappers serve /health/live; the api serves /api/v1/health/live).
ENV PORT=8000 HEALTHCHECK_PATH=/api/v1/health/live

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT}${HEALTHCHECK_PATH}" || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/start.sh"]
