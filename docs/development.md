# Desarrollo

## Requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (gestor de dependencias y lock)
- Docker / Docker Compose (Server Host de referencia)
- PostgreSQL 16 (Compose o instancia local)

## Setup nativo

```bash
uv sync --frozen --all-extras
cp .env.example .env
```

Activa el entorno de uv (`.venv`) o usa `uv run ...`.

Configura `DATABASE_URL` o `EXCELER_DB_*` apuntando a PostgreSQL.

### Actualizar dependencias

```bash
# editar rangos en pyproject.toml si hace falta
uv lock
uv sync --frozen --all-extras
```

Revisa el diff de `uv.lock` en el PR. No uses un segundo gestor de dependencias en paralelo.

## Comandos útiles

```bash
uv run exceler db upgrade
uv run uvicorn exceler.main:app --reload --port 8000
uv run exceler source list
uv run pytest
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy
```

## CI

GitHub Actions ejecuta en `push`/`pull_request` a `main`:

- `ruff format --check`, `ruff check`, `mypy`
- `pytest` (con PostgreSQL de servicio)
- `docker build` (instalación desde `uv.lock`)

## Estructura

```text
src/exceler/
  api/             # FastAPI
  application/     # casos de uso
  domain/          # modelo y reglas (sin FastAPI/SQLAlchemy)
  infrastructure/  # adaptadores
  cli/             # Typer
  config/          # settings y secretos
  main.py
```

Dependencias conceptuales: API/CLI → Application → Domain/Ports ← Infrastructure.

## Pruebas de API con PostgreSQL

```bash
# Windows PowerShell
$env:TEST_DATABASE_URL="postgresql+psycopg://exceler:pass@localhost:5432/exceler"
uv run pytest
```

Las pruebas de dominio y liveness no requieren base de datos.

## OpenAPI

Con la API en marcha: `http://127.0.0.1:8000/docs`.
