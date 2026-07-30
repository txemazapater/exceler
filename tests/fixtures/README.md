# Synthetic Excel fixtures (Phase 2.0)

Corpus sintético, determinista y versionado. **No** contiene datos corporativos reales.
Los generadores viven en `tests/generators/` y no forman parte del dominio productivo.

**Fuente de verdad:** `tests.generators.catalog.ALL_SPECS`.
`index.json` es un artefacto derivado; `verify` falla si diverge.

## Layout

```text
tests/fixtures/
├── workbooks/     # binarios .xlsx / .xlsm pequeños versionados
├── manifests/     # intención deliberada del generador
├── expected/      # oráculos (schema_version + expectations)
├── index.json
└── README.md
```

Categorías: `minimal`, `structural`, `types`, `quality`, `relationships`, `scenarios`.

## Comandos

```bash
uv run exceler dev fixtures generate
uv run exceler dev fixtures verify
# equivalente:
uv run python -m tests.generators.generate_fixtures
uv run python -m tests.generators.verify_fixtures
```

Semilla por defecto: `20260730`.

La regeneración de comprobación usa directorios temporales aislados (`tempfile`), no un scratch compartido versionado.

## Cómo añadir un escenario

1. Definir el comportamiento futuro a validar.
2. Añadir un builder en `tests/generators/` (seed fija).
3. Registrar un `ScenarioSpec` en el catálogo (`structural_scenarios` / `corporate_scenarios`).
4. Ejecutar `exceler dev fixtures generate`.
5. Revisar manifiesto + workbook + expected skeleton.
6. Ejecutar `exceler dev fixtures verify` y tests unitarios.
7. Ampliar `expected/` cuando exista la capacidad del motor (**2A+**).

## Seguridad

- No ejecutar macros.
- No seguir enlaces externos ni red.
- No incluir secretos ni datos reales.
- `xlsm_container.xlsm`: extensión `.xlsm` **sin** `vbaProject.bin` (aceptación segura; sin macros).

## Escenario corporativo inicial

`workbooks/scenarios/hell_erp/`:

- `clientes.xlsx`, `articulos.xlsx`, `pedidos.xlsx`, `lineas_pedido.xlsx`, `facturas.xlsx`

Relaciones deliberadas y anomalías controladas (duplicados, FK inexistente, fechas texto, totales, hoja auxiliar, sinónimos de columnas).

Ver `docs/fixtures.md`.
