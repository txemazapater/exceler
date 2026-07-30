# Changelog

Formato inspirado en [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- Fase 2A: Workbook Inspection Foundation (`WorkbookInspection`, `OpenPyxlWorkbookReader`, CLI `workbook inspect`).
- Corpus 2A ampliado (tipos físicos, veryHidden, freeze/autofilter, VBA stub, dimensión inflada, tablas avanzadas, …).
- Documentación `docs/workbook-inspection.md`, `docs/limitations.md`, ADR 0005.

### Changed

- Fase 2.0 endurecida: instantánea lógica ampliada, expected `schema_version`, índice validado, regen en `TemporaryDirectory`, pruebas negativas del verificador.
- Nomenclatura inequívoca del roadmap (Alternativa B): 2.0 / 2S / 2A–2E.
- CI: disparo manual `workflow_dispatch`.
- Expected fixtures: contrato `expectations.inspection` (+ secciones reservadas 2B/2E).

### Added (prev)

- Fase 2.0: corpus sintético Excel (generadores deterministas, fixtures, manifiestos, expected skeletons).
- CLI `exceler dev fixtures generate|verify` y verificación en CI.
- Escenario corporativo `hell_erp` (clientes/artículos/pedidos/líneas/facturas).
- Documentación `docs/fixtures.md`.
- Estrategia de pruebas en tres niveles (unit / integration / docker) sin exigir Docker local.
- Fakes en memoria; smoke Compose; staging SAPIENS.

## [0.0.0] — 2026-07-30

### Added

- Repositorio inicial con README de estado.
