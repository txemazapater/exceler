# Roadmap

Roadmap incremental. Las fases son orden de aprendizaje y entrega, no un compromiso de calendario.

Estado actual: **Fase 1 en implementación** (registro de orígenes). Fase 0.1 documentalmente cerrada.

## Fase 0 — Fundamentos

- Visión, alcance y principios.
- Arquitectura de subsistemas y contratos conceptuales.
- Modelo de dominio y terminología.
- Seguridad y criterios tecnológicos.
- Repositorio documental y proceso ADR.
- Estrategia de pruebas con muestras sintéticas (documentada).

**Salida:** base documental inicial.

## Fase 0.1 — Corrección del modelo temporal y de ejecución

- `AssetSnapshot` como ancla del análisis reproducible.
- Ejecuciones distintas: `DiscoveryRun`, `InspectionRun`, `ProfilingRun`, `InferenceRun`.
- `CandidateRelationship` con extremos explícitos.
- Separación `EvidenceItem` / `ConfidenceAssessment`.
- `ReviewDecision` generalizada a sujetos revisables.
- Presencia y accesibilidad como dimensiones ortogonales.
- Information Graph reconocido como modelo conceptual desde el inicio.
- Adelanto de SMB y SharePoint/OneDrive en el roadmap de conectores.

**Salida:** dominio y arquitectura coherentes antes de implementar. Ver [ADR 0001](decisions/0001-phase-0-1-domain-and-execution-model.md).

## Fase 1 — Registro de orígenes

- Modelo de `DiscoverySource`.
- Validación de configuración y rutas filesystem bajo raíces permitidas.
- Declaración de capacidades esperadas (filesystem en esta fase).
- `CredentialReference` (abstracción; sin secretos en claro).
- Persistencia PostgreSQL + migraciones Alembic.
- API REST + CLI administrativa.
- Auditoría esencial de cambios.
- Docker Compose de referencia.

**Salida:** orígenes configurables y validables sin enumeración completa de archivos ni análisis Excel.

## Fase 2 — Conector de sistema de archivos

- Rutas locales y montadas.
- Enumeración y filtros include/exclude.
- Metadatos básicos; presencia vs accesibilidad.
- Hash opcional; contribución a `AssetSnapshot`.
- Errores normalizados.
- Pruebas de no mutación del origen.

**Salida:** primer conector útil en entornos controlados.

## Fase 3 — Inventario y ejecuciones de descubrimiento

- `DiscoveredAsset`, `DiscoveryRun`, `DiscoveryObservation`, `AssetSnapshot`.
- Nuevos / modificados / no observados / potencialmente eliminados.
- Histórico sin borrado inmediato por desaparición.
- Resumen de ejecución.
- Alimentación inicial del Information Graph conceptual (persistencia mínima de relaciones de inventario).

**Salida:** inventario reproducible entre runs.

## Fase 4 — Conector SMB

- Recursos SMB/CIFS.
- Autenticación vía `CredentialReference`.
- Enumeración, filtros, metadatos, errores normalizados.
- Paridad de contrato con el conector de filesystem (presencia, accesibilidad, snapshot).

**Salida:** descubrimiento en compartidos de red empresariales típicos.

## Fase 5 — Conectores SharePoint / OneDrive

- Bibliotecas y rutas documentales Microsoft 365 / SharePoint.
- Identificadores externos estables cuando el origen los ofrezca.
- Metadatos, versiones si la capacidad existe, límites y errores normalizados.
- Solo lectura; sin alterar permisos ni contenidos.

**Salida:** cobertura de orígenes documentales cloud frecuentes.

## Fase 6 — Inspección estructural de Excel

- `InspectionRun`.
- Formatos soportados (prioridad XLSX/XLSM; XLS según viabilidad).
- Hojas, rangos, tablas, nombres, fórmulas, vínculos.
- Detección de macros **sin ejecución**.
- `ObservedWorkbook` anclado a `AssetSnapshot`.

**Salida:** modelo observado factual.

## Fase 7 — Perfilado de datos

- `ProfilingRun`.
- Tipos aparentes, nulos, unicidad, cardinalidad.
- Patrones, distribuciones, anomalías.
- `EvidenceItem` factuales; límites de muestreo y sensibilidad.

**Salida:** `Profile` ligado a campos/regiones observadas.

## Fase 8 — Inferencia inicial

- `InferenceRun`.
- Encabezados y entidades candidatas.
- Campos y tipos candidatos.
- Claves candidatas.
- Relaciones internas con extremos explícitos.
- `EvidenceItem` + `ConfidenceAssessment` + `ReviewDecision`.

**Salida:** primer modelo inferido revisable.

## Fase 9 — Relaciones entre libros

- Similitud de esquemas y datos.
- Claves compartidas y duplicidades.
- Linaje probable entre archivos.
- Extremos inter-libro, confianza y conflictos.

**Salida:** propuestas inter-libro.

## Fase 10 — Navegación del Information Graph

- Materialización consultable del grafo ya conceptual.
- Consultas y navegación.
- Visualización (formato libre; tecnología por ADR).

**Salida:** exploración operativa del conocimiento acumulado (el grafo no “nace” aquí; se opera).

## Fase 11 — Consolidación asistida

- Propuestas de modelo canónico.
- Conflictos y duplicados.
- Mappings.
- Flujo de revisión humana generalizada.

**Salida:** canónico aprobado de forma asistida.

## Fase 12 — Generación de esquema

- Destinos: SQL Server, PostgreSQL, SQLite (u otros acordados).
- Scripts reproducibles.
- Sin migración automática ciega.

**Salida:** materialización de esquema a partir del canónico.

## Más allá (indicativo)

- SFTP y otros protocolos;
- agentes en equipos remotos;
- reporting ejecutivo sistemático;
- otros tipos de documento (CSV, Access, JSON, …);
- ejecución distribuida;
- CLI / servicio según necesidad.

## Dependencias entre fases

```mermaid
flowchart LR
  F0[0 Fundamentos] --> F01[0.1 Modelo]
  F01 --> F1[1 Orígenes]
  F1 --> F2[2 FS]
  F2 --> F3[3 Inventario]
  F3 --> F4[4 SMB]
  F3 --> F6[6 Inspector]
  F4 --> F5[5 SPO/OD]
  F6 --> F7[7 Profiling]
  F7 --> F8[8 Inferencia]
  F8 --> F9[9 Inter-libro]
  F3 --> F10[10 Grafo nav.]
  F8 --> F10
  F9 --> F10
  F10 --> F11[11 Consolidación]
  F11 --> F12[12 Schema]
```

SMB (4) y SharePoint/OneDrive (5) pueden avanzar en paralelo al inicio de la inspección (6) cuando el inventario (3) ya sea usable.

## Criterio para avanzar de fase

No se considera cerrada una fase solo por existir código esqueleto. Debe haber:

- contratos claros;
- pruebas reproducibles cuando haya implementación;
- documentación alineada con el comportamiento real;
- ADR si se fija tecnología o se cambia el dominio.

## Relacionados

- Alcance: [scope.md](scope.md)
- Arquitectura: [architecture.md](architecture.md)
- Dominio: [domain-model.md](domain-model.md)
