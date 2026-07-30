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

## Contenido

| Tipo | Ubicación | Notas |
|------|-----------|-------|
| Generadores | `tests/generators/` | Solo tests/dev; semilla fija |
| Binarios | `tests/fixtures/workbooks/` | Pequeños, versionados |
| Manifiestos | `tests/fixtures/manifests/` | Intención del generador |
| Expected | `tests/fixtures/expected/` | Esqueleto para oráculos futuros |

## Comandos

```bash
uv run exceler dev fixtures generate
uv run exceler dev fixtures verify
uv run pytest -m "not integration and not docker"
```

CI ejecuta `fixtures verify` en el job `quality`.

## Subfases posteriores

Antes de cada subfase (2A–2E) se amplía primero el corpus correspondiente. Ver roadmap.

## Restricción

El dominio/aplicación productivos **no** importan `tests` ni conocen fixtures.
