# Changelog

Formato inspirado en [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- Estrategia de pruebas en tres niveles (unit / integration / docker) sin exigir Docker local.
- Fakes en memoria para repositorio y auditoría; tests de aplicación locales.
- Smoke test Compose en CI (`scripts/compose_smoke.sh`).
- `compose.staging.yaml` y `docs/staging.md` (SAPIENS / Traefik, despliegue manual).

### Changed

- Marcadores pytest declarados; comando local `pytest -m "not integration and not docker"`.
- CI separado en jobs quality, integration y docker.
- Compose base sin `container_name` fijos (proyectos aislados con `-p`).

### Changed (prev)

- Crear/actualizar un origen valida configuración, no accesibilidad actual.
- `POST /api/v1/sources/{id}/validate` devuelve resultado estructurado.
- Health separado: `/health/live` y `/health/ready`.
- `credential_reference` exige esquemas `env://` o `file://`.
- `DiscoverySource.reconfigure()` protege campos e invariantes.
- Dependencias reproducibles con `uv.lock`.

### Added (prev)

- ADR 0004 — hosts Server/Native/Desktop/Agent.
- GitHub Actions inicial y Fase 1 ejecutable.

## [0.0.0] — 2026-07-30

### Added

- Repositorio inicial con README de estado.
