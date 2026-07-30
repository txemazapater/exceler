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
- JSON: `regions_schema_version` = **2**
- Detector: `2B.2`
- Inspección de entrada: schema **3** (estilos enriquecidos: font/fill/alignment/borders)

### Capas de ocupación (contrato)

No son intercambiables:

| Capa | Significado | Uso |
|------|-------------|-----|
| **observed** | Celdas en `WorkbookInspection.cells` | Trazabilidad 2A |
| **content** | Valor no nulo o fórmula | Densidad / `empty_ratio` / ratios de tipo |
| **visual** | Contenido + vacías con estilo + cobertura de merges | Conectividad Union-Find |

`RegionStatistics` expone `observed_count`, `content_occupied_count`, `visual_occupied_count`,
`occupied_count` (= content), `density` (content/área) y `visual_density`.

### Tablas estructuradas

Los `tables[]` de 2A **reservan** su interior: la heurística solo corre fuera de esos bbox.
La semilla estructurada es autoridad (`confidence=1`, ref exacta). Así no hay regiones
duplicadas ni solapes parciales mal absorbidos.

## Algoritmo MVP

1. Capas de ocupación desde celdas observadas + expansión visual de `merged_ranges` (sin inventar contenido en no-anclas).
2. Reservar interiores de tablas estructuradas.
3. Componentes 4-conectados sobre ocupación **visual** residual.
4. Refinado: fusión a través de huecos vacíos débiles según continuidad de estilo/borde.
5. Clasificación por puntuación (`title` / `table` / `note` / `unknown`) usando densidad de **contenido**.
6. Cabecera/pie candidatos; anidación ligera título→tabla.
7. Semillas estructuradas + regiones heurísticas.
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
| `false_gap_inside_table` | hueco interior **no** divide (visual) |
| `styled_separator_blocks` | cambio de fill divide |
| `structured_table_partial_overlap` | tabla Excel + columna adyacente separada |

## Fuera de alcance (2B)

Chart/image geometry, pivot caches, AI/ML, perfilado de columnas, claves, relaciones (2C–2E).
