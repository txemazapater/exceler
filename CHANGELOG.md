# Changelog

Formato inspirado en [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Changed

- Fase 2B contrato endurecido (`regions_schema_version` 2 / detector `2B.2`): ocupación en capas
  (observed/content/visual) y tablas estructuradas que reservan su interior ante solapes parciales.

### Added

- Fase 2B: detección de regiones lógicas (`HeuristicRegionDetector`, CLI `workbook regions`, `expectations.regions`).
- Corpus 2B: footer, notas, nesting, false-gap, separadores por estilo, solape parcial con tabla estructurada.
- Inspección schema **3**: estilos factuales (font/fill/alignment/borders) para continuidad visual.

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
