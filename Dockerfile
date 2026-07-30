# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system exceler \
    && useradd --system --gid exceler --create-home --home-dir /home/exceler exceler \
    && mkdir -p /app /work /tmp/exceler /sources \
    && chown -R exceler:exceler /app /work /tmp/exceler /home/exceler

COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /usr/local/bin/uv

WORKDIR /app

COPY --chown=exceler:exceler pyproject.toml uv.lock README.md LICENSE alembic.ini ./
COPY --chown=exceler:exceler src ./src
COPY --chown=exceler:exceler alembic ./alembic
COPY --chown=exceler:exceler tests ./tests

USER exceler
RUN uv sync --frozen --no-dev

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=25s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/health/live || exit 1

CMD ["uvicorn", "exceler.main:app", "--host", "0.0.0.0", "--port", "8000"]
