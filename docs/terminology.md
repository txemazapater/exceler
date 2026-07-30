# Terminología

Glosario del dominio EXCELER (Fase 0.1). Si un documento usa un término de forma distinta, prevalece este glosario hasta que un ADR lo cambie.

## Acceso e inventario

| Término | Definición |
|---------|------------|
| **Origen** (`DiscoverySource`) | Ubicación explorable caracterizada por endpoint, mecanismo de acceso, identidad, alcance y política. No es solo una ruta. |
| **Conector** | Adaptador capaz de validar, conectar, enumerar y leer un tipo de origen en solo lectura, declarando capacidades. |
| **Capacidad de conector** | Función soportada por un conector (listar, leer, hash, versiones, etc.). |
| **Activo** (`DiscoveredAsset`) | Identidad durable de un archivo o documento en el inventario. |
| **Observación** (`DiscoveryObservation`) | Registro de presencia/intento de acceso de un activo en una `DiscoveryRun`. |
| **Snapshot de activo** (`AssetSnapshot`) | Captura puntual en inventario/captura (no modelo observado) usada como entrada estable del análisis. |
| **Snapshot lógico** | Captura identificada por hash, tamaño, fecha, ETag, versión externa y metadatos. |
| **Snapshot materializado** | Captura que conserva o referencia bytes concretos analizados. |
| **Estado de materialización** | `metadata_only`, `temporary_content`, `retained_content`, `external_version_reference`, `unavailable`. |
| **Política de retención de contenido** (`ContentRetentionPolicy`) | Reglas de conservación/limpieza de bytes de un snapshot. |
| **Ejecución de descubrimiento** (`DiscoveryRun`) | Exploración/listado acotado en el tiempo sobre un origen. |
| **Presencia** | Dimensión de inventario: si el activo se observa o no respecto al origen (`present`, `not_observed`, `potentially_removed`, …). |
| **Accesibilidad** | Dimensión ortogonal: si un intento de lectura pudo completarse (`accessible`, `locked`, `permission_denied`, …). |
| **Referencia de credencial** | Identificador lógico de un secreto almacenado fuera del modelo de origen. |

## Ejecuciones de análisis

| Término | Definición |
|---------|------------|
| **Ejecución de inspección** (`InspectionRun`) | Análisis estructural factual sobre uno o más snapshots. |
| **Ejecución de perfilado** (`ProfilingRun`) | Cálculo de perfiles sobre campos/regiones observadas. |
| **Ejecución de inferencia** (`InferenceRun`) | Generación de candidatos de modelo e evidencias asociadas. |

## Estructura Excel / documento

| Término | Definición |
|---------|------------|
| **Libro** (`ObservedWorkbook`) | Descripción factual de un workbook Excel observado a partir de un snapshot. |
| **Hoja** (`ObservedWorksheet`) | Worksheet observada dentro de un libro. |
| **Región** (`ObservedRegion`) | Área delimitada dentro de una hoja (tabla, rango, bloque) tratada como unidad de análisis. |
| **Tabla** | Región con estructura tabular explícita o detectada; en capa observada no implica entidad de negocio. |
| **Campo observado** (`ObservedField`) | Columna o atributo factual dentro de una región. |

## Interpretación

| Término | Definición |
|---------|------------|
| **Entidad** | Concepto de negocio. En fase temprana suele ser **entidad inferida** (candidata), no canónica. |
| **Campo** | Atributo de una entidad. Distinguir campo observado, inferido y canónico. |
| **Clave candidata** | Propuesta de identificador único o estable, aún no aprobada. |
| **Relación candidata** | Propuesta de vínculo con **extremos explícitos** (sujeto, rol, cardinalidad en cada lado). |
| **Extremo de relación** | Extremo from/to de una `CandidateRelationship`. |
| **Evidencia** (`EvidenceItem`) | Hecho o medición unitaria que sostiene o debilita una afirmación; no es una puntuación. |
| **Evaluación de confianza** (`ConfidenceAssessment`) | Juicio de confianza derivado de evidencias, con método/versión; prioriza revisión, no certifica verdad. |
| **Perfil** | Resumen estadístico/estructural de valores de un campo o región. |
| **Sujeto revisable** | Cualquier objeto sobre el que puede recaer una `ReviewDecision`. |

## Modelos

| Término | Definición |
|---------|------------|
| **Modelo observado** | Hechos estructurales y de contenido sin reinterpretación de negocio, anclados a snapshots. |
| **Modelo inferido** | Propuestas con evidencias, evaluaciones de confianza y estado de revisión. |
| **Modelo canónico** | Estructura corporativa aprobada; independiente de un archivo concreto. |
| **Information Graph** | Vista relacional conceptual entre orígenes, activos, estructuras, inferencias, decisiones y canónicos. Existe desde el inicio como modelo; su motor/UI son posteriores. |
| **Mapping** | Correspondencia entre elementos observados/inferidos y elementos canónicos. |
| **Consolidación** | Proceso de proponer y acordar un modelo canónico a partir de múltiples fuentes. |
| **Linaje** | Cadena de procedencia: origen → activo → observación/snapshot → estructura → perfil → inferencia → decisión → canónico. |

## Gobierno

| Término | Definición |
|---------|------------|
| **Inferencia** | Propuesta automática o asistida; nunca afirmación absoluta por sí sola. |
| **Decisión de revisión** | Acto generalizado de aprobar, rechazar, diferir o pedir más evidencia sobre un sujeto revisable. |
| **Solo lectura** | Modo operativo que prohíbe mutar el origen. |
| **Inventario** | Estado histórico de activos, observaciones y snapshots; no es el modelo canónico. |

## Distinciones críticas

- **Origen ≠ conector:** el origen se configura; el conector sabe operarlo.
- **Activo ≠ snapshot:** el activo es la identidad; el snapshot es lo capturado en un momento.
- **Snapshot ≠ modelo observado:** el snapshot es captura; el libro observado es estructura factual derivada por inspección.
- **Presencia ≠ accesibilidad:** no listar un archivo no es lo mismo que no poder leerlo.
- **Activo ≠ libro observado:** el libro es descripción estructural factual de un snapshot.
- **Tabla ≠ entidad:** una tabla observada puede inspirar una entidad inferida, pero no la es automáticamente.
- **Evidencia ≠ confianza:** los hechos se registran aparte del juicio de puntuación.
- **Inferido ≠ canónico:** lo propuesto no es lo aprobado.
- **Confianza ≠ certeza / aprobación:** una puntuación alta no elimina la revisión.
- **Grafo conceptual ≠ fase de visualización:** el grafo existe como modelo desde el inicio.

## Relacionados

- Dominio: [domain-model.md](domain-model.md)
- Arquitectura: [architecture.md](architecture.md)
