# EXCELER

**Exceler** — motor de descubrimiento de almacenes informales de información corporativa.

EXCELER aborda un problema habitual en empresas y organizaciones: la proliferación descontrolada de archivos Excel usados como bases de datos no gobernadas.

## Estado del proyecto

**Fase 2A en curso:** inspección factual de workbooks (`.xlsx`/`.xlsm`) sin interpretación.
Fase 2.0 cerrada (corpus sintético). Aún **no** hay detección de tablas/tipos/claves/relaciones.

CI: GitHub Actions (`quality` + unit + fixture verify, `integration` + Postgres, `docker` build + Compose smoke).
Local sin Docker: `pytest -m "not integration and not docker"`.
Staging manual: [docs/staging.md](docs/staging.md).
Fixtures: `uv run exceler dev fixtures generate|verify`.
Inspección: `uv run exceler workbook inspect path.xlsx [--format json]`.

## Arranque rápido (Docker Compose)

```bash
cp .env.example .env
cp secrets/db_password.example secrets/db_password
docker compose up --build
docker compose exec exceler-app exceler db upgrade
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
```

Desarrollo nativo con lock reproducible (sin Docker local):

```bash
uv sync --frozen --all-extras
uv run pytest -m "not integration and not docker"
```

OpenAPI: http://127.0.0.1:8000/docs

Detalle: [docs/deployment.md](docs/deployment.md), [docs/development.md](docs/development.md), [docs/configuration.md](docs/configuration.md), [docs/staging.md](docs/staging.md).

## El problema

Los libros Excel corporativos suelen acumular, sin diseño previo, datos maestros, operativos, catálogos, controles, fórmulas y copias divergentes. Excel acaba siendo una base de datos informal; el coste aparece al consolidar.

## Qué pretende descubrir

1. dónde están esos archivos;
2. cómo se accede a cada ubicación;
3. qué activos existen, sin modificar las fuentes;
4. estructura y contenido observable;
5. entidades, campos, claves y relaciones candidatas;
6. un modelo de información corporativa;
7. esquemas consolidados posibles;
8. trazabilidad origen → inferencia → modelo aprobado.

## Principios fundamentales

1. Descubrimiento antes que transformación.
2. Solo lectura sobre los orígenes.
3. Separación entre acceso y análisis.
4. Trazabilidad completa.
5. Inferencias, no afirmaciones absolutas.
6. Seguridad y mínimo privilegio (credenciales por referencia).
7. Arquitectura evolutiva (Excel primero, sin acoplar el núcleo).

## Fuera del alcance actual

CRUD de negocio / SPA / app de escritorio; edición de orígenes; SMB/SharePoint directos; inspección Excel; perfilado; inferencia; generación SQL; colas; Kubernetes; motor de grafos.

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [docs/vision.md](docs/vision.md) | Visión |
| [docs/scope.md](docs/scope.md) | Alcance |
| [docs/architecture.md](docs/architecture.md) | Arquitectura |
| [docs/domain-model.md](docs/domain-model.md) | Dominio |
| [docs/terminology.md](docs/terminology.md) | Glosario |
| [docs/security.md](docs/security.md) | Seguridad |
| [docs/roadmap.md](docs/roadmap.md) | Roadmap |
| [docs/deployment.md](docs/deployment.md) | Despliegue Compose |
| [docs/development.md](docs/development.md) | Desarrollo |
| [docs/configuration.md](docs/configuration.md) | Configuración y secretos |
| [docs/fixtures.md](docs/fixtures.md) | Corpus sintético Excel (Fase 2.0) |
| [docs/workbook-inspection.md](docs/workbook-inspection.md) | Inspección factual (Fase 2A) |
| [docs/limitations.md](docs/limitations.md) | Limitaciones conocidas |
| [docs/staging.md](docs/staging.md) | Staging manual en SAPIENS |
| [docs/decisions/](docs/decisions/README.md) | ADRs |

## API (Fase 1)

```text
GET    /health                 # alias liveness
GET    /health/live
GET    /health/ready
GET    /api/v1/sources
POST   /api/v1/sources
GET    /api/v1/sources/{id}
PUT    /api/v1/sources/{id}
PATCH  /api/v1/sources/{id}/status
DELETE /api/v1/sources/{id}          # archiva (soft-delete)
POST   /api/v1/sources/{id}/validate # accesibilidad estructurada
```

Crear/actualizar valida **configuración**. `validate` diagnostica **accesibilidad** en el nodo actual.

## CLI

```bash
exceler db upgrade
exceler source list
exceler source validate <id>
exceler workbook inspect archivo.xlsx
exceler workbook inspect archivo.xlsx --format json --pretty
exceler dev fixtures generate
exceler dev fixtures verify
```

## Licencia

[MIT](LICENSE) — Copyright (c) 2026 txemazapater.

## Contribución

Ver [CONTRIBUTING.md](CONTRIBUTING.md).
