# Changelog

Formato inspirado en [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- Fase 2A hardening: identidad por `sha256(payload)`, `cells_scanned`/`cells_observed`, inspección `complete`/`partial`, schema JSON 2, exit CLI 7.
- Fixtures patológicos: `pathological_inflated_dimension`, `moderately_inflated_dimension`, `max_observed_cells_partial`.

### Changed

- Fase 2A marcada como cerrada tras hardening de límites e identidad.
- `WorkbookSource` ya no exige `content_hash()` en el protocolo.

### Added (prev)

- Fase 2A: Workbook Inspection Foundation (`WorkbookInspection`, `OpenPyxlWorkbookReader`, CLI `workbook inspect`).
- Corpus 2A ampliado (tipos físicos, veryHidden, freeze/autofilter, VBA stub, dimensión inflada, tablas avanzadas, …).
- Documentación `docs/workbook-inspection.md`, `docs/limitations.md`, ADR 0005.
- Fase 2.0 endurecida / corpus sintético / verify CI.

## [0.0.0] — 2026-07-30

### Added

- Repositorio inicial con README de estado.
