# Profiling and type inference (Phase 2C)

Perfilado estadístico e inferencia de tipos **estructurales** a partir de:

```text
WorkbookInspection + RegionDetectionResult → ProfilingResult
```

El profiler **no** reabre Excel ni importa openpyxl.

## Flujo CLI

```bash
uv run exceler workbook profile archivo.xlsx
uv run exceler workbook profile archivo.xlsx --format json --pretty
```

Ejecuta inspect → regions → profile en una sola lectura.

## Contrato

- Dominio: `exceler.domain.profiling`
- Implementación: `DeterministicRegionProfiler`
- `profiling_schema_version` = **1**
- `profiler_version` = **2C.2**
- Conserva `inspector_version`, `region_detector_version`, `regions_schema_version`

Hash de workbook debe coincidir entre 2A y 2B (`ProfilingInputMismatchError` si no).

## Capas de valor

Por celda de datos (bbox − header − footer):

| Concepto | Significado |
|----------|-------------|
| unobserved | sin celda en la inspección |
| null | observada sin valor |
| blank string | `""` |
| whitespace-only | solo espacios |
| formula | expresión presente, **sin** valor evaluado |
| error | error Excel |
| content | valor usable para inferencia |

## Tipos lógicos

Estructurales (`LogicalValueType`): unknown, empty, boolean, integer, decimal, number, text, code, identifier, date, datetime, time, percentage, currency, email, url, phone, postal_code, uuid.

Salida: tipo seleccionado + confianza + alternativas + evidencias + anomalías.
Sin entidades de negocio ni PK definitivas.

## Decisiones

1. Celdas vía **bbox + índice de inspección** (no exige `cell_coordinates`).
2. Sin tipo `MIXED`: distribución física + baja confianza / unknown.
3. Locale ambigua (`03/04/2026`, `1.234`) reduce confianza / excluye del parseo;
   no se impone DD/MM, MM/DD ni separador decimal anglosajón.
4. Formato Excel es evidencia, no verdad.
5. Identifiers/categories son **candidatos**.
6. Confianza ≈ compatibilidad × suficiencia de muestra × penalización por anomalías
   (`sample_sufficiency_full_at`, `high_compatibility_ratio`, `moderate_compatibility_ratio`).
7. `PERCENTAGE` / `CURRENCY` ganan a `DECIMAL`/`NUMBER` cuando hay señal de formato/símbolo.
8. `distinct_ratio` = distinct / content; `unique_ratio` = singletons / content.
   La candidatura a identificador usa `distinct_ratio`.
9. Enteros/decimales como texto cuentan si el parseo es inequívoco; ceros iniciales
   no se promocionan a INTEGER.
10. Compatibilidad y anomalías comparten `check_compatibility` (un solo criterio por tipo).
11. Estadísticas temporales ordenan por valor parseado, no por orden lexicográfico del texto.

`profiler_version` = **2C.2** (algoritmo; schema sigue en 1).

## Escenarios de corpus

`profile_core_types`, `profile_logical_specials`, `profile_mixed_and_anomalies`,
`profile_id_and_category`, `profile_headers` — expectativas parciales en
`expectations.profiling`.

## Fuera de alcance

Semántica de negocio, relaciones, SQL, AI, evaluación de fórmulas, relectura del workbook.
