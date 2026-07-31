# Changelog

Formato inspirado en [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- Fase 2C: perfilado e inferencia de tipos estructurales (`DeterministicRegionProfiler`, CLI
  `workbook profile`, `expectations.profiling`, corpus de tipos/anomalías/ids).
- Documentación `docs/profiling-and-type-inference.md`.

### Changed

- Profiler **2C.3**: matriz explícita DATE/DATETIME/TIME (un `09:30` ya no es
  compatible con DATE; DATE sí promociona a DATETIME).
- Profiler **2C.2**: parseo numérico sin locale fija, enteros/decimales como texto,
  `unique_ratio` = singletons/content, fechas ordenadas por valor parseado, compatibilidad
  centralizada para inferencia y anomalías.
- Fase 2B contrato endurecido (`regions_schema_version` 2 / detector `2B.2`): ocupación en capas
  (observed/content/visual) y tablas estructuradas que reservan su interior ante solapes parciales.
- Roadmap/README: siguiente corte **2D**.

### Changed

- Fase 2B marcada como cerrada; siguiente corte 2C.
- README/roadmap/limitations actualizados para regiones.

### Added (prev)

- Fase 2A hardening: identidad por `sha256(payload)`, `cells_scanned`/`cells_observed`, inspección `complete`/`partial`, schema JSON 2, exit CLI 7.
- Fixtures patológicos: `pathological_inflated_dimension`, `moderately_inflated_dimension`, `max_observed_cells_partial`.

### Changed (prev)

- Fase 2A marcada como cerrada tras hardening de límites e identidad.
- `WorkbookSource` ya no exige `content_hash()` en el protocolo.

### Added (earlier)

- Fase 2A: Workbook Inspection Foundation (`WorkbookInspection`, `OpenPyxlWorkbookReader`, CLI `workbook inspect`).
- Corpus 2A ampliado (tipos físicos, veryHidden, freeze/autofilter, VBA stub, dimensión inflada, tablas avanzadas, …).
- Documentación `docs/workbook-inspection.md`, `docs/limitations.md`, ADR 0005.
- Fase 2.0 endurecida / corpus sintético / verify CI.

## [0.0.0] — 2026-07-30

### Added

- Repositorio inicial con README de estado.
