# Changelog

Formato inspirado en [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Changed

- Crear/actualizar un origen valida configuración, no accesibilidad actual.
- `POST /api/v1/sources/{id}/validate` devuelve resultado estructurado (`configuration_valid`, `accessible`, `errors`).
- Health separado: `/health/live` y `/health/ready` (Compose usa readiness).
- `credential_reference` exige esquemas `env://` o `file://`.
- `DiscoverySource.reconfigure()` protege campos e invariantes.
- Dependencias reproducibles con `uv.lock`; Docker e instalación vía `uv sync --frozen`.

### Added

- ADR 0004 — hosts Server/Native/Desktop/Agent.
- GitHub Actions CI (quality, tests+Postgres, docker-build).
- Fase 1 ejecutable previa, ADRs 0002–0003 y documentación de despliegue.

## [0.0.0] — 2026-07-30

### Added

- Repositorio inicial con README de estado.
