# Region detection (Phase 2B)

Detección determinista de regiones lógicas a partir de un `WorkbookInspection` (Fase 2A).
El detector **no** reabre Excel ni importa openpyxl.

## Flujo

```text
WorkbookSource → OpenPyxlWorkbookReader → WorkbookInspection
                                         → HeuristicRegionDetector → RegionDetectionResult
```

CLI: `exceler workbook regions <path>` ejecuta inspect + detect en una sola pasada de lectura.

## Modelo

- Dominio: `exceler.domain.regions` (`LogicalRegion`, `BoundingBox`, `RegionType`, …)
- Puerto: `RegionDetector.detect(inspection, options)`
- Implementación: `exceler.application.regions.heuristic_detector.HeuristicRegionDetector`
- JSON: `regions_schema_version` = **1**
- Inspección de entrada: schema **3** (estilos enriquecidos: font/fill/alignment/borders)

## Algoritmo MVP

1. Ocupación desde celdas observadas + expansión de `merged_ranges`.
2. Componentes 4-conectados (Union-Find).
3. Refinado: fusión a través de huecos vacíos débiles según continuidad de estilo/borde (no fusiona gaps fuertes ni bandas título↔tabla).
4. Clasificación por puntuación: `title` / `table` / `note` / `unknown` (resto de `RegionType` reservado).
5. Candidatos de cabecera/pie dentro de tablas (índices de fila).
6. Anidación ligera: título padre de tabla adyacente con span compatible.
7. Semillas de alta confianza desde tablas estructuradas Excel (`tables[]` de 2A).
8. Confianza = peso de evidencia normalizado en `[0, 1]`.

## CLI

```bash
uv run exceler workbook regions archivo.xlsx
uv run exceler workbook regions archivo.xlsx --format json --pretty
```

Mismos códigos de salida que `workbook inspect` (incl. **7** si la inspección fue parcial).

## Corpus / contratos

Escenarios con `expectations.regions` (comparador parcial `compare_region_expectations`):

| scenario | intención |
|----------|-----------|
| `two_regions_one_sheet` | 2 tablas lado a lado |
| `title_above_header` | título + tabla |
| `table_with_totals_footer` | footer de totales |
| `note_block_below_table` | nota separada |
| `nested_title_and_table` | parent/child |
| `false_gap_inside_table` | hueco interior **no** divide |
| `styled_separator_blocks` | cambio de fill divide |

## Fuera de alcance (2B)

Chart/image geometry, pivot caches, AI/ML, perfilado de columnas, claves, relaciones (2C–2E).
