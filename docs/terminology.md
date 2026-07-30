# Terminología

Glosario inicial del dominio EXCELER. Si un documento usa un término de forma distinta, prevalece este glosario hasta que un ADR lo cambie.

## Acceso e inventario

| Término | Definición |
|---------|------------|
| **Origen** (`DiscoverySource`) | Ubicación explorable caracterizada por endpoint, mecanismo de acceso, identidad, alcance y política. No es solo una ruta. |
| **Conector** | Adaptador capaz de validar, conectar, enumerar y leer un tipo de origen en solo lectura, declarando capacidades. |
| **Capacidad de conector** | Función soportada por un conector (listar, leer, hash, versiones, etc.). |
| **Activo** (`DiscoveredAsset`) | Archivo o documento inventariado a partir de un origen. |
| **Observación** (`DiscoveryObservation`) | Registro de haber visto (o dejado de ver) un activo en una ejecución concreta. |
| **Ejecución de descubrimiento** (`DiscoveryRun`) | Exploración acotada en el tiempo sobre un origen. |
| **Referencia de credencial** | Identificador lógico de un secreto almacenado fuera del modelo de origen. |

## Estructura Excel / documento

| Término | Definición |
|---------|------------|
| **Libro** (`ObservedWorkbook`) | Descripción factual de un workbook Excel observado. |
| **Hoja** (`ObservedWorksheet`) | Worksheet observada dentro de un libro. |
| **Región** (`ObservedRegion`) | Área delimitada dentro de una hoja (tabla, rango, bloque) tratada como unidad de análisis. |
| **Tabla** | Región con estructura tabular explícita (p. ej. Tabla de Excel) o detectada; en capa observada no implica entidad de negocio. |
| **Campo observado** (`ObservedField`) | Columna o atributo factual dentro de una región. |

## Interpretación

| Término | Definición |
|---------|------------|
| **Entidad** | Concepto de negocio. En fase temprana suele ser **entidad inferida** (candidata), no canónica. |
| **Campo** | Atributo de una entidad. Distinguir campo observado, inferido y canónico. |
| **Clave candidata** | Propuesta de identificador único o estable, aún no aprobada. |
| **Relación candidata** | Propuesta de vínculo entre entidades/campos, con evidencia y confianza. |
| **Evidencia** | Hecho observable que sostiene una inferencia. |
| **Confianza** | Puntuación o nivel que prioriza revisión; no certifica verdad. |
| **Perfil** | Resumen estadístico/estructural de valores de un campo o región. |

## Modelos

| Término | Definición |
|---------|------------|
| **Modelo observado** | Conjunto de hechos estructurales y de contenido sin reinterpretación de negocio. |
| **Modelo inferido** | Conjunto de propuestas (entidades, claves, relaciones, etc.) con evidencia y estado de revisión. |
| **Modelo canónico** | Estructura corporativa aprobada; independiente de un archivo concreto. |
| **Mapping** | Correspondencia entre elementos observados/inferidos y elementos canónicos. |
| **Consolidación** | Proceso de proponer y acordar un modelo canónico a partir de múltiples fuentes. |
| **Linaje** | Cadena de procedencia: origen → activo → observación → estructura → inferencia → decisión → canónico. |

## Gobierno

| Término | Definición |
|---------|------------|
| **Inferencia** | Propuesta automática o asistida; nunca afirmación absoluta por sí sola. |
| **Decisión de revisión** | Acto de aprobar, rechazar o diferir una propuesta. |
| **Solo lectura** | Modo operativo que prohíbe mutar el origen. |
| **Inventario** | Estado histórico de activos y observaciones; no es el modelo canónico. |

## Distinciones críticas

- **Origen ≠ conector:** el origen se configura; el conector sabe operarlo.
- **Activo ≠ libro observado:** el activo es la identidad inventariada; el libro es la descripción estructural factual.
- **Tabla ≠ entidad:** una tabla observada puede inspirar una entidad inferida, pero no la es automáticamente.
- **Inferido ≠ canónico:** lo propuesto no es lo aprobado.
- **Confianza ≠ certeza:** una puntuación alta no elimina la revisión.

## Relacionados

- Dominio: [domain-model.md](domain-model.md)
- Arquitectura: [architecture.md](architecture.md)
