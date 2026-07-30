# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/home/exceler/.local/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system exceler \
    && useradd --system --gid exceler --create-home --home-dir /home/exceler exceler \
    && mkdir -p /app /work /tmp/exceler /sources \
    && chown -R exceler:exceler /app /work /tmp/exceler /home/exceler

WORKDIR /app

COPY --chown=exceler:exceler pyproject.toml README.md LICENSE alembic.ini ./
COPY --chown=exceler:exceler src ./src
COPY --chown=exceler:exceler alembic ./alembic
COPY --chown=exceler:exceler tests ./tests

USER exceler
RUN pip install --user -e ".[dev]"

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "exceler.main:app", "--host", "0.0.0.0", "--port", "8000"]
