# Desarrollo

## Requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (gestor de dependencias y lock)
- Docker / Docker Compose **solo** para jobs CI o staging (no obligatorio en el puesto local de Cursor)
- PostgreSQL 16 **solo** para pruebas de integración (CI o instancia opcional)

## Tres niveles de prueba

| Nivel | Marcador | Requiere | Comando |
|-------|----------|----------|---------|
| Unitario / aplicación | `unit` (y tests sin marcador infra) | Python | `pytest -m "not integration and not docker"` |
| Integración | `integration` | PostgreSQL | `pytest -m integration` |
| Docker / Compose | CI `docker` job | Docker | `bash scripts/compose_smoke.sh` |

En el puesto local **sin Docker**, el flujo de calidad es:

```bash
uv sync --frozen --all-extras
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy
uv run pytest -m "not integration and not docker"
```

La evidencia de PostgreSQL + imagen + Compose queda en **GitHub Actions**.
El staging manual en **SAPIENS** se documenta en [staging.md](staging.md).

## Setup nativo

```bash
uv sync --frozen --all-extras
cp .env.example .env
```

### Actualizar dependencias

```bash
uv lock
uv sync --frozen --all-extras
```

## Comandos útiles

```bash
uv run exceler db upgrade
uv run uvicorn exceler.main:app --reload --port 8000
uv run exceler source list
uv run pytest -m "not integration and not docker"
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy
```

## CI

GitHub Actions en `push`/`pull_request` a `main`:

1. quality — format, lint, mypy, unit tests
2. integration — pytest con PostgreSQL service
3. docker — `docker build` + smoke Compose (secretos sintéticos, migrate, health, API mínima, logs si falla)

## Estructura

```text
src/exceler/
  api/
  application/
  domain/
  infrastructure/
  cli/
  config/
  main.py
tests/
  fakes.py                 # repositorio/auditoría en memoria
  test_*.py
scripts/compose_smoke.sh
```

## OpenAPI

Con la API en marcha: `http://127.0.0.1:8000/docs`.
