# Muestras sintéticas

Los libros Excel de prueba versionados viven en:

```text
tests/fixtures/workbooks/
```

Ver [tests/fixtures/README.md](../tests/fixtures/README.md) y [docs/fixtures.md](../docs/fixtures.md).

`samples/sources/` sigue siendo un directorio vacío de ejemplo para mounts Docker (sin datos corporativos).

## Reglas

- Solo datos ficticios.
- Generación determinista con semilla fija.
- No macros ejecutables en tests.
- Ampliar el corpus **antes** de implementar capacidades del motor.
