# Contribuir a EXCELER

EXCELER está en **fase de definición arquitectónica**. Las contribuciones útiles ahora son documentales y de diseño, no implementaciones prematuras.

## Principios al contribuir

- Respeta los [principios fundamentales](README.md#principios-fundamentales).
- Usa el vocabulario de [docs/terminology.md](docs/terminology.md).
- No mezcles modelo observado, inferido y canónico.
- No asumas tecnologías no decididas en ADR.
- No introduzcas archivos corporativos reales; solo muestras sintéticas documentadas.

## Cambios documentales

1. Mantén coherencia entre `README.md` y `docs/`.
2. Si introduces un término nuevo, añádelo al glosario.
3. Si tomas una decisión arquitectónica real, crea un ADR en `docs/decisions/`.
4. Actualiza `CHANGELOG.md` bajo `[Unreleased]`.

## Cambios de código (cuando existan)

Todavía no hay árbol de código. Cuando se inicie la implementación:

- las pruebas deben ser reproducibles;
- los conectores no deben contener lógica de interpretación Excel;
- el análisis no debe ejecutar macros;
- los orígenes se tratan en solo lectura.

## Decisiones tecnológicas

No propongas un stack como hecho consumado. Usa [docs/technology-selection.md](docs/technology-selection.md) y, si procede, un ADR.
