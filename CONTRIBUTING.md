# Contribuir a EXCELER

## Principios

- Respeta los principios del [README](README.md).
- Usa el vocabulario de [docs/terminology.md](docs/terminology.md).
- No mezcles modelo observado, inferido y canónico.
- Los cambios semánticos de dominio requieren ADR; los renombres editoriales no.
- No introduzcas archivos corporativos reales ni secretos.

## Desarrollo

Ver [docs/development.md](docs/development.md).

Antes de un PR de código:

```bash
ruff format src tests
ruff check src tests
mypy
pytest
```

## Decisiones tecnológicas

Consultar [docs/decisions/](docs/decisions/README.md). No propongas stacks alternativos en código sin ADR.
