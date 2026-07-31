# Corpus sintético de libros Excel (Fase 2.0)

EXCELER no implementa todavía el Discovery Engine de Excel. Esta infraestructura es el **laboratorio** previo obligatorio.

## Principio

Cada capacidad futura se valida contra un escenario sintético diseñado a propósito:

1. definir comportamiento esperado;
2. crear/ampliar escenario;
3. definir resultado esperado;
4. escribir prueba;
5. implementar;
6. verificar no-regresión.

## Fuente de verdad

El catálogo Python `tests.generators.catalog.ALL_SPECS` es la **única fuente de verdad**.

`tests/fixtures/index.json` se genera a partir del catálogo y `verify` falla si diverge.
No deben mantenerse dos inventarios independientes.

## Contenido

| Tipo | Ubicación | Notas |
|------|-----------|-------|
| Generadores | `tests/generators/` | Solo tests/dev; semilla fija |
| Binarios | `tests/fixtures/workbooks/` | Pequeños, versionados |
| Manifiestos | `tests/fixtures/manifests/` | Intención del generador |
| Expected | `tests/fixtures/expected/` | Oráculos (`schema_version`) |
| Índice | `tests/fixtures/index.json` | Derivado del catálogo |

## Equivalencia de fixtures

Dos fixtures son equivalentes cuando su **contenido lógico** (hojas, celdas, ocultación, tablas, nombres, etc.) coincide.
No se usa el hash binario ZIP/XLSX como criterio de fallo (solo diagnóstico opcional).

## Comandos

```bash
uv run exceler dev fixtures generate
uv run exceler dev fixtures verify
uv run pytest -m "not integration and not docker"
```

CI ejecuta `fixtures verify` en el job `quality` (también `workflow_dispatch`).

## XLSM

`xlsm_container.xlsm` es un libro con extensión `.xlsm` **sin** `vbaProject.bin`.
Sirve para aceptar de forma segura la extensión; no contiene macros ejecutables y nunca se invocan vía Excel/COM.

## Cortes posteriores (nomenclatura B)

**2A** inspection (activa) → **2B** regions → **2C** profiling → **2D** keys → **2E** relationships.
**2S** es inventario filesystem (paralelo). Ver [roadmap.md](roadmap.md).

Durante 2A/2B/2C se validan `expectations.inspection`, `expectations.regions` y, cuando existe,
`expectations.profiling`. Secciones `relationships` / keys pueden existir como reservadas.

## Restricción

El dominio/aplicación productivos **no** importan `tests` ni conocen fixtures.
