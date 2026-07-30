# Workbook Inspection (Phase 2A) — **cerrada**

Observador factual de libros Excel. **No** interpreta tablas lógicas, tipos semánticos, claves ni relaciones.

## Alcance

El inspector describe:

- formato (`xlsx` / `xlsm`);
- hojas (orden, visibilidad, dimensión declarada, freeze, autofiltro);
- celdas relevantes (valor físico, `library_data_type`, `number_format`, fórmula, comentario, hipervínculo);
- tablas estructuradas declaradas;
- rangos combinados;
- nombres definidos;
- enlaces externos detectables (sin seguirlos);
- presencia de `vbaProject.bin` (sin ejecutarlo);
- `completion_status` completo/parcial y truncamientos estructurados.

## Identidad del archivo

`FileIdentity.content_hash` = `sha256(payload)` de los **mismos bytes** entregados a openpyxl.
`FileIdentity.size_bytes` = `len(payload)`.

No se vuelve a abrir el origen para hashear. Si `source.size_bytes()` ≠ `len(payload)`, se emite `SOURCE_SIZE_CHANGED` y se usa el payload.

## cells_scanned vs cells_observed

| Métrica | Significado |
|---------|-------------|
| `cells_scanned` | Posiciones examinadas durante el recorrido |
| `cells_observed` | Celdas incluidas en `WorksheetInspection.cells` |

## Límites por defecto

| Límite | Valor | Efecto |
|--------|------:|--------|
| `max_file_size_bytes` | 512 MiB | Abort (`WorkbookLimitExceededError`, exit 6) |
| `max_worksheets` | 1_000 | Abort |
| `max_cells_observed` | 2_000_000 | Inspección **parcial** (exit 7) |
| `max_cells_scanned` | 5_000_000 | Inspección **parcial**; si el área declarada lo supera, fallback a celdas materializadas |

### Dimensiones patológicas

Si `max_row * max_column >` presupuesto de escaneo restante, **no** se hace `iter_rows` del rectángulo completo.
El adaptador inspecciona solo celdas materializadas (`worksheet._cells`, encapsulado en infraestructura) y marca:

- `completion_status: partial`
- `truncation_reasons`: `MAX_CELLS_SCANNED`
- warning `MATERIALIZED_CELLS_FALLBACK`

Esto es una medida de seguridad de ejecución, **no** detección de regiones (2B).

## Completitud

```text
completion_status: complete | partial
truncation_reasons: [{code, message, location?}, ...]
```

Códigos: `MAX_CELLS_OBSERVED`, `MAX_CELLS_SCANNED`, `MAX_WORKSHEETS`.

## Formatos

| Formato | Soporte 2A |
|--------|------------|
| `.xlsx` | sí |
| `.xlsm` | sí (lectura segura) |
| `.xls` | no |

## Seguridad

- `data_only=False` — preserva fórmulas; no las evalúa.
- `keep_vba=False` — no carga VBA para ejecución; la presencia se detecta por ZIP.
- `keep_links=True` — metadatos de enlaces; nunca descarga ni red.
- No escribe el origen; no invoca Excel/COM.

## CLI

```bash
uv run exceler workbook inspect archivo.xlsx
uv run exceler workbook inspect archivo.xlsx --format json --pretty
uv run exceler workbook inspect archivo.xlsx --max-cells 100000 --max-cells-scanned 500000
```

### Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | OK, inspección completa |
| 1 | error inesperado |
| 2 | argumentos inválidos |
| 3 | formato no soportado |
| 4 | no encontrado / inaccesible |
| 5 | inválido o cifrado |
| 6 | límite duro (archivo/hojas) |
| 7 | inspección **parcial** (JSON/texto válidos) |

## Modelo / puerto

- Dominio: `exceler.domain.workbook`
- Puerto: `WorkbookReader` / `WorkbookSource` (sin `content_hash` en el protocolo)
- Adaptador: `OpenPyxlWorkbookReader` + `LocalWorkbookSource`
- JSON: inspección `schema_version` = **2**

## Limitaciones conocidas

Ver [limitations.md](limitations.md).
