# Desarrollo

## Requisitos

- Python 3.12+
- Docker / Docker Compose (entorno de referencia)
- PostgreSQL 16 (Compose o instancia local)

## Setup nativo

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Configura `DATABASE_URL` o `EXCELER_DB_*` apuntando a PostgreSQL.

## Comandos útiles

```bash
exceler db upgrade
uvicorn exceler.main:app --reload --port 8000
exceler source list
pytest
ruff check src tests
ruff format src tests
mypy
```

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
set TEST_DATABASE_URL=postgresql+psycopg://exceler:pass@localhost:5432/exceler
pytest
```

En Compose, tras `db upgrade`:

```bash
docker compose exec -e TEST_DATABASE_URL=postgresql+psycopg://exceler:$(cat /run/secrets/db_password)@exceler-db:5432/exceler exceler-app pytest
```

Las pruebas de dominio no requieren base de datos.

## OpenAPI

Con la API en marcha: `http://127.0.0.1:8000/docs`.
