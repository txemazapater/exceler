# Workbook Inspection (Phase 2A)

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
- presencia de `vbaProject.bin` (sin ejecutarlo).

No responde a: “esto es una tabla de clientes”, “CodCli es PK”, etc. (fases 2B–2E).

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
uv run exceler workbook inspect archivo.xlsx --output out.json --format json
uv run exceler workbook inspect archivo.xlsx --max-cells 100000
```

### Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | OK |
| 1 | error inesperado |
| 2 | argumentos inválidos |
| 3 | formato no soportado |
| 4 | no encontrado / inaccesible |
| 5 | inválido o cifrado |
| 6 | límite de seguridad |

## Modelo / puerto

- Dominio: `exceler.domain.workbook`
- Puerto: `WorkbookReader` / `WorkbookSource`
- Adaptador: `OpenPyxlWorkbookReader` + `LocalWorkbookSource`
- JSON: `schema_version` de inspección = **1** (independiente del schema de fixtures)

## Límites por defecto

- `max_worksheets`: 1000
- `max_cells`: 2_000_000
- `max_file_size_bytes`: 512 MiB

## Limitaciones conocidas

Ver [limitations.md](limitations.md).
