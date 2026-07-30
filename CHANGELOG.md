# Changelog

Formato inspirado en [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Changed

- Fase 2.0 endurecida: instantánea lógica ampliada, expected `schema_version`, índice validado, regen en `TemporaryDirectory`, pruebas negativas del verificador.
- Nomenclatura inequívoca del roadmap (Alternativa B): 2.0 / 2S / 2A–2E.
- CI: disparo manual `workflow_dispatch`.

### Added

- Fase 2.0: corpus sintético Excel (generadores deterministas, fixtures, manifiestos, expected skeletons).
- CLI `exceler dev fixtures generate|verify` y verificación en CI.
- Escenario corporativo `hell_erp` (clientes/artículos/pedidos/líneas/facturas).
- Documentación `docs/fixtures.md`.

### Added (prev)

- Estrategia de pruebas en tres niveles (unit / integration / docker) sin exigir Docker local.
- Fakes en memoria; smoke Compose; staging SAPIENS.

## [0.0.0] — 2026-07-30

### Added

- Repositorio inicial con README de estado.
