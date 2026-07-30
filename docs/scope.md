# Alcance

## Alcance inicial (Fases 0 / 0.1)

La definición arquitectónica incluye:

- visión, principios y límites;
- modelo de dominio (incl. corrección 0.1: snapshots, runs de análisis, evidencia/confianza, revisión generalizada);
- subsistemas y contratos conceptuales;
- glosario y criterios de seguridad;
- roadmap incremental;
- proceso ADR y muestras sintéticas documentadas.

No incluye software ejecutable.

## Alcance posterior (previsto)

Por fases posteriores, según [roadmap.md](roadmap.md):

| Área | Contenido previsto |
|------|--------------------|
| Orígenes | Registro, validación, capacidades, referencias de credenciales |
| Conectores | Filesystem; SMB; SharePoint/OneDrive (adelantados tras el inventario inicial) |
| Inventario | Activos, observaciones, snapshots, presencia vs accesibilidad, `DiscoveryRun` |
| Excel | `InspectionRun`; estructura sin modificar ni ejecutar macros |
| Perfilado | `ProfilingRun`; tipos aparentes, nulos, unicidad, patrones, anomalías |
| Inferencia | `InferenceRun`; entidades, campos, claves y relaciones con extremos explícitos |
| Grafo | Conceptual desde el inicio; navegación/materialización en fase dedicada |
| Consolidación | Propuestas, conflictos, mappings, `ReviewDecision` generalizada |
| Esquemas | Generación asistida hacia SQL Server, PostgreSQL, SQLite u otros |
| Informes | Salidas técnicas y ejecutivas (p. ej. Markdown/HTML) |

## Fuera de alcance (por ahora)

Queda explícitamente fuera:

- CRUD para usuario final;
- SPA (Vue u otra);
- aplicación de escritorio como producto inicial;
- edición de archivos origen;
- renombrado, movimiento o eliminación de fuentes;
- migración automática sin validación humana;
- eliminación automática de duplicados;
- modificación de permisos en los orígenes;
- ejecución de macros durante el análisis;
- importación masiva automática a una base de datos productiva;
- almacenamiento de secretos en claro dentro de la configuración de orígenes;
- incorporación de datos corporativos reales como muestras del repositorio.

## Supuestos

- Las organizaciones permiten identidades técnicas de **solo lectura** sobre los orígenes a explorar.
- Existirá revisión humana antes de aprobar modelos canónicos o esquemas generados.
- Los libros de prueba del repositorio serán **sintéticos** y no contendrán datos reales.
- El primer formato prioritario será Excel moderno (XLSX/XLSM); XLS podrá abordarse después.
- Puede ser necesario operar en Windows y Linux.
- No todos los orígenes ofrecerán identificadores externos estables; el inventario debe tolerarlo.

## Restricciones

- El descubrimiento no debe ser intrusivo sobre las fuentes.
- Conectores y analizadores permanecen desacoplados.
- Modelo observado, inferido y canónico no se mezclan.
- Las tecnologías de implementación permanecen abiertas hasta ADR explícitos.
- No se añadirá CI hasta que exista código real que validar.
- La licencia del proyecto es MIT.

## Relación con otras piezas

- Visión: [vision.md](vision.md)
- Arquitectura: [architecture.md](architecture.md)
- Seguridad: [security.md](security.md)
- Roadmap: [roadmap.md](roadmap.md)
