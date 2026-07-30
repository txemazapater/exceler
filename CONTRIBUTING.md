# Contribuir a EXCELER

## Principios

- Respeta los principios del [README](README.md).
- Usa el vocabulario de [docs/terminology.md](docs/terminology.md).
- No mezcles modelo observado, inferido y canónico.
- Los cambios semánticos de dominio requieren ADR; los renombres editoriales no.
- No introduzcas archivos corporativos reales ni secretos.

## Desarrollo

Ver [docs/development.md](docs/development.md).

Antes de un PR de código (sin Docker local):

```bash
uv run ruff format src tests
uv run ruff check src tests
uv run mypy
uv run pytest -m "not integration and not docker"
```

Mantén `uv.lock` actualizado si cambias dependencias (`uv lock`).
PostgreSQL/Docker se validan en CI; staging manual en SAPIENS.

## Decisiones tecnológicas

Consultar [docs/decisions/](docs/decisions/README.md). No propongas stacks alternativos en código sin ADR.
