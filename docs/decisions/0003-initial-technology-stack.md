# ADR 0003 — Stack tecnológico inicial

- **Estado:** accepted
- **Fecha:** 2026-07-30
- **Decisores:** proyecto EXCELER

## Contexto

La Fase 1 requiere API, persistencia, migraciones, validación, CLI, logging y pruebas, con vista a lectura robusta de XLSX/XLSM (sin macros), conectores desacoplados y ejecución en Windows y Linux.

Criterios en [technology-selection.md](../technology-selection.md).

## Decisión

| Área | Elección |
|------|----------|
| Lenguaje / runtime | **Python 3.12+** |
| API | **FastAPI** |
| Validación / settings | **Pydantic v2** + **pydantic-settings** |
| ORM / DB access | **SQLAlchemy 2.x** |
| Migraciones | **Alembic** |
| Persistencia | **PostgreSQL 16** |
| CLI | **Typer** |
| Logging | logging estándar con formatter JSON estructurado |
| Pruebas | **pytest**, **httpx**, Testcontainers o PostgreSQL de Compose según contexto |
| Lint / format / types | **Ruff**, **mypy** |
| Configuración | variables de entorno + archivos example; secretos por referencia |
| Empaquetado | paquete `exceler` instalable (`src/` layout) |

### Justificación breve

- **Python:** ecosistema maduro para ZIP/XML y Excel; tipado gradual con mypy; mismo runtime para API, CLI y futuros workers; fácil de contenerizar.
- **FastAPI + Pydantic:** OpenAPI automático, validación estricta, buen encaje con contratos de API.
- **SQLAlchemy + Alembic + PostgreSQL:** modelo relacional claro para inventario/auditoría; JSONB para `connector_settings` sin opacificar todo el dominio; migraciones versionadas.
- **Typer:** CLI delgada que reutiliza la capa de aplicación.

### DELETE de orígenes

`DELETE /api/v1/sources/{id}` **archiva** (`archived_at`); no borra físicamente la fila. Coherente con no perder configuración/auditoría. Un hard-delete, si algún día se necesita, será operación administrativa explícita.

## Alternativas consideradas

- **Go** — excelente para conectores y binarios; ecosistema Excel/XML menos cómodo para la fase de análisis.
- **.NET** — fuerte en Windows/Excel; peor simetría Linux/contenedores para el equipo y el despliegue de referencia.
- **Node/TypeScript** — buena API; más débil para procesamiento documental pesado y tipado de dominio a largo plazo.
- **SQLite como primaria** — simple para demos; insuficiente para concurrencia, JSONB rico y evolución multi-instancia.
- **Django** — válido; FastAPI es más ligero para API-first + CLI compartida sin acoplar plantillas/admin.

La biblioteca concreta de lectura Excel se decidirá en un ADR futuro al abrir la Fase 6 (inspección).

## Consecuencias

### Positivas

- Un solo lenguaje para API/CLI/tests.
- Camino claro hacia inspectores Excel sin cambiar de runtime.
- Persistencia alineada con auditoría y linaje.

### Negativas / riesgos

- GIL y aislamiento de procesos: el parsing de archivos potencialmente maliciosos deberá aislarse (proceso/contenedor) en fases posteriores.
- Disciplina de tipado (mypy) necesaria para no degradar el dominio.

### Seguimiento

- No introducir Redis, colas, MinIO ni motor de grafos en esta fase.
- Revisar ADR de librería Excel antes de Fase 6.

## Referencias

- [technology-selection.md](../technology-selection.md)
- [ADR 0002](0002-runtime-and-deployment-strategy.md)
- [architecture.md](../architecture.md)
