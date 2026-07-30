# ADR 0005 — openpyxl as Phase 2A workbook reader

- **Estado:** accepted
- **Fecha:** 2026-07-30
- **Decisores:** proyecto EXCELER

## Contexto

La Fase 2A requiere observación factual de `.xlsx` / `.xlsm` sin ejecutar macros ni evaluar fórmulas. ADR 0003 dejó abierta la biblioteca concreta.

## Decisión

Usar **openpyxl** como adaptador de infraestructura (`OpenPyxlWorkbookReader`).

- Dependencia de producción (no solo dev).
- El dominio y la aplicación no importan openpyxl.
- Opciones: `data_only=False`, `keep_vba=False`, `keep_links=True`, `read_only=False` (necesario para tablas/estilos/merges en 2A).

## Alternativas

- **xlrd / pyxlsb / xlwings** — fuera de alcance (xls/binarios o automatización Excel).
- **Solo zip/xml propio** — coste alto para tablas/nombres/estilos.

## Consecuencias

- Limitaciones documentadas en `docs/limitations.md`.
- Un segundo adaptador requeriría ADR nuevo.

## Referencias

- [workbook-inspection.md](../workbook-inspection.md)
- [ADR 0003](0003-initial-technology-stack.md)
