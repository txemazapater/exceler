# Modelo de dominio

Modelo conceptual (Fase 0.1). Los nombres pueden evolucionar mediante ADR; deben permanecer coherentes con [terminology.md](terminology.md).

## Capas

| Capa | Pregunta que responde | Ejemplos |
|------|----------------------|----------|
| Observado | ¿Qué se vio, sin reinterpretar? | `ObservedWorkbook`, `ObservedField`, `AssetSnapshot` |
| Inferido | ¿Qué proponemos y con qué evidencia? | `InferredEntity`, `CandidateKey`, `CandidateRelationship` |
| Canónico | ¿Qué se aprobó como estructura corporativa? | `CanonicalEntity`, `Mapping` |

El **Information Graph** es la vista relacional de estas capas: existe como modelo conceptual desde el inicio. Su materialización consultable/visual es una fase de implementación posterior, no el momento en que “aparece” el grafo.

## Estados ortogonales: presencia y accesibilidad

No se mezclan.

| Dimensión | Pregunta | Valores conceptuales (indicativos) |
|-----------|----------|--------------------------------------|
| **Presencia** | ¿El activo se ha visto en el origen respecto al inventario? | `present`, `not_observed`, `potentially_removed` |
| **Accesibilidad** | ¿Pudo el conector leer metadatos/contenido cuando lo intentó? | `accessible`, `locked`, `permission_denied`, `not_found`, `transient_error`, `unsupported`, `unknown` |

Un activo puede estar **presente** en el listado y ser **inaccesible** a la lectura (p. ej. bloqueado). Puede dejar de observarse en una run (`not_observed` / `potentially_removed`) sin borrarse del inventario. La desaparición no implica eliminación inmediata del registro.

## Ejecuciones

Además de `DiscoveryRun`, el análisis tiene ejecuciones propias:

| Ejecución | Produce principalmente |
|-----------|------------------------|
| `DiscoveryRun` | observaciones de inventario / presencia |
| `InspectionRun` | modelo observado (`ObservedWorkbook`, …) |
| `ProfilingRun` | `Profile` |
| `InferenceRun` | entidades, claves, relaciones candidatas |

Cada ejecución registra inicio/fin, estado, errores, versión del componente y referencias a entradas/salidas. Discovery y análisis no comparten un único “run” genérico ambiguo.

## Mapa de relaciones (vista compacta)

```mermaid
erDiagram
  DiscoverySource ||--o{ DiscoveryRun : executes
  DiscoverySource }o--o| CredentialReference : uses
  DiscoverySource ||--o{ DiscoveredAsset : discovers
  DiscoveryRun ||--o{ DiscoveryObservation : records
  DiscoveredAsset ||--o{ DiscoveryObservation : observed_as
  DiscoveredAsset ||--o{ AssetSnapshot : snapshots
  DiscoveryObservation }o--o| AssetSnapshot : may_capture
  AssetSnapshot ||--o{ InspectionRun : inspected_by
  InspectionRun ||--o| ObservedWorkbook : produces
  ObservedWorkbook ||--o{ ObservedWorksheet : contains
  ObservedWorksheet ||--o{ ObservedRegion : contains
  ObservedRegion ||--o{ ObservedField : contains
  ObservedField ||--o{ ProfilingRun : profiled_in
  ProfilingRun ||--o{ Profile : produces
  InferenceRun }o--o{ AssetSnapshot : uses
  InferenceRun ||--o{ InferredEntity : produces
  InferredEntity ||--o{ InferredField : has
  InferredEntity ||--o{ CandidateKey : proposes
  CandidateRelationship }o--|| RelationshipEndpoint : from
  CandidateRelationship }o--|| RelationshipEndpoint : to
  EvidenceItem }o--o| ReviewableSubject : about
  ConfidenceAssessment }o--|| ReviewableSubject : scores
  ConfidenceAssessment }o--o{ EvidenceItem : based_on
  ReviewDecision }o--|| ReviewableSubject : decides
  CanonicalEntity ||--o{ CanonicalField : has
  Mapping }o--|| CanonicalEntity : targets
```

`ReviewableSubject` y `RelationshipEndpoint` son roles conceptuales (polimórficos), no necesariamente tablas físicas.

## Entidades conceptuales

### DiscoverySource

Ubicación explorable con mecanismo de acceso, identidad, alcance y política.

**Responsabilidad:** definir *dónde* y *cómo* se puede descubrir, no *qué significa* el contenido.

**Atributos conceptuales típicos:** identificador, nombre, tipo, endpoint, ubicación raíz, mecanismo de autenticación, `CredentialReference`, habilitado/deshabilitado, modo solo lectura, recursividad, patrones include/exclude, límites operativos, frecuencia/política, última ejecución correcta, último error, configuración específica del conector.

**Relaciones:** usa `CredentialReference`; origina `DiscoveryRun` y `DiscoveredAsset`.

### CredentialReference

Puntero a un secreto en un almacén externo o proveedor de identidad.

**Responsabilidad:** desacoplar configuración de origen y material secreto.

**No almacena** usuario/contraseña/token en el registro del origen.

### ConnectorCapability

Declaración de lo que un conector puede hacer (listar, leer contenido, metadatos, permisos, versiones, historial, hash, detectar cambios, archivos bloqueados, etc.).

**Responsabilidad:** permitir al coordinador adaptar la exploración a lo disponible.

### DiscoveredAsset

Identidad durable de un archivo o documento en el inventario.

**Distingue:**

- identidad interna EXCELER;
- identificador externo estable (si el origen lo ofrece);
- ubicación visible actual o última conocida;
- **estado de presencia** agregado (derivado de observaciones);
- **última accesibilidad conocida** (derivada de intentos de lectura; ortogonal a presencia);
- historial de observaciones y snapshots.

**No confunde** “no listado en la última run” con “no legible”, ni borra el activo al dejar de observarse.

**Relaciones:** pertenece a un `DiscoverySource`; acumula `DiscoveryObservation` y `AssetSnapshot`.

### DiscoveryRun

Ejecución de exploración/listado sobre un origen.

**Recoge:** inicio/fin, estado, contadores (encontrados, nuevos, modificados, no observados, omitidos), errores, volumen enumerado/leído según política, versión del conector.

### DiscoveryObservation

Hecho de inventario en una run: el activo se listó, se intentó leer metadatos, o se constató su ausencia respecto a la expectativa.

**Incluye, de forma separada:**

- resultado de **presencia** en esa run;
- resultado de **accesibilidad** si hubo intento de lectura;
- metadatos ligeros observados (tamaño, mtime, etag, …) cuando existan.

**Responsabilidad:** historial fino sin forzar borrado del activo.

### AssetSnapshot

Captura puntual del activo usada como entrada estable para inspección, perfilado e inferencia.

**Responsabilidad:** congelar *qué contenido/metadatos se analizaron*, frente a la identidad mutable del `DiscoveredAsset`.

**Atributos conceptuales típicos:** enlace al activo; opcionalmente a la observación que motivó la captura; instante; huella/hash; tamaño; indicador de accesibilidad en el momento de captura; referencia a bytes o materialización temporal (con política de retención/limpieza); versión del conector que leyó.

Sin snapshot no debería afirmarse un `ObservedWorkbook` reproducible: el modelo observado cuelga del snapshot, no solo del activo vivo.

### InspectionRun

Ejecución del Workbook Inspector (u otro inspector de documento) sobre uno o más `AssetSnapshot`.

**Produce:** `ObservedWorkbook` y estructura asociada; registra versión del inspector, errores y cobertura.

### ObservedWorkbook

Descripción factual de un libro Excel derivada de un `AssetSnapshot` vía `InspectionRun`.

**Conserva lo observado:** formato, hojas, dimensiones, tablas, rangos, nombres definidos, fórmulas, celdas combinadas, validaciones, vínculos externos, consultas, macros detectadas, propiedades, características.

**No interpreta** todavía entidades de negocio.

### ObservedWorksheet

Hoja observada dentro de un libro.

### ObservedRegion

Región o área tabular candidata dentro de una hoja (tabla Excel, rango usado, bloque detectado, etc.).

### ObservedField

Columna o campo observado dentro de una región (encabezado aparente, posición, muestras estructurales).

### ProfilingRun

Ejecución del Profiling Engine sobre regiones/campos observados (anclados a un snapshot/inspección).

**Produce:** uno o más `Profile`; registra versión, muestreo aplicado y errores.

### Profile

Resultado de perfilado: tipos aparentes, nulos, unicidad, cardinalidad, patrones, distribuciones, anomalías.

### InferenceRun

Ejecución del Inference Engine.

**Consume:** estructura observada, perfiles y, cuando proceda, contexto inter-libro.

**Produce:** `InferredEntity`, `InferredField`, `CandidateKey`, `CandidateRelationship`, `EvidenceItem` asociados; registra versión del motor.

### InferredEntity

Entidad de negocio candidata.

Sujeto revisable. No incrusta “la” confianza como atributo opaco único: la confianza se modela con `ConfidenceAssessment` sobre evidencias.

### InferredField

Campo candidato perteneciente a una entidad inferida, con tipo candidato y linaje hacia `ObservedField` / región / hoja / libro / snapshot.

### CandidateKey

Propuesta de clave (natural, compuesta, surrogate aparente) con evidencias de unicidad/estabilidad. Sujeto revisable.

### CandidateRelationship

Propuesta de relación con **extremos explícitos**.

Cada extremo (`RelationshipEndpoint`) declara:

- sujeto (entidad inferida o campo inferido);
- rol opcional (p. ej. padre/hijo, lookup/fact);
- cardinalidad candidata en ese extremo.

La relación incluye tipo candidato (asociación, dependencia, copia, linaje probable, …), evidencias y es sujeto revisable.

**No es válido** una relación “sueltas” sin extremos identificables.

### EvidenceItem

Hecho unitario que sostiene (o debilita) una afirmación.

**Incluye conceptualmente:**

- tipo de evidencia (unicidad, solapamiento de valores, coincidencia de nombres, vínculo externo, …);
- sujeto o afirmación a la que aplica;
- referencias a orígenes factuales (campo observado, perfil, snapshot, …);
- resumen o payload minimizado (sin retener PII de más);
- ejecución que la produjo (`ProfilingRun` / `InferenceRun` / …);
- instante.

Las evidencias **no** son puntuaciones: son hechos o mediciones.

### ConfidenceAssessment

Juicio de confianza **separado** de la evidencia.

**Incluye conceptualmente:**

- sujeto revisable evaluado (entidad, clave, relación, campo, …);
- conjunto de `EvidenceItem` considerados;
- método o política de puntuación y su versión;
- valor o banda de confianza;
- instante y componente que la calculó.

Puede haber varias evaluaciones en el tiempo para el mismo sujeto. Una puntuación alta **no** equivale a aprobación.

### CanonicalEntity / CanonicalField

Elementos aprobados del modelo corporativo consolidado. Separados de las inferencias que los motivaron.

### Mapping

Correspondencia entre elementos observados/inferidos y elementos canónicos. Sujeto revisable.

### ReviewDecision

Decisión de revisión **generalizada** sobre cualquier sujeto revisable.

**Sujetos típicos:** `InferredEntity`, `InferredField`, `CandidateKey`, `CandidateRelationship`, `Mapping`, propuestas de `CanonicalEntity` / `CanonicalField`, y otros que el gobierno defina.

**Resultados típicos:** aprobar, rechazar, diferir, pedir más evidencia, solicitar enmienda.

**Registra:** sujeto, resultado, actor, instante, comentario, decisión previa opcional, y vínculos a evidencias/evaluaciones consultadas.

No está limitada a mappings ni a un único tipo de inferencia.

## Responsabilidades por capa (resumen)

| Capa | Puede afirmar | No debe afirmar |
|------|---------------|-----------------|
| Observado | “En el snapshot S, la hoja X tiene una tabla en A1:D200” | “Es la entidad Cliente” |
| Inferido | “Hay evidencia de entidad Cliente; evaluación de confianza 0.72 (método M v1)” | “Este es el modelo oficial” |
| Canónico | “Cliente.Codigo es clave aprobada” | “El archivo origen ya está migrado” |

## Ciclo de vida simplificado

1. Se configura un `DiscoverySource` con `CredentialReference`.
2. Un `DiscoveryRun` enumera activos y registra `DiscoveryObservation` (presencia ≠ accesibilidad).
3. Cuando procede leer contenido, se materializa un `AssetSnapshot`.
4. Un `InspectionRun` produce `ObservedWorkbook` desde el snapshot.
5. Un `ProfilingRun` produce `Profile`.
6. Un `InferenceRun` propone entidades/claves/relaciones, emite `EvidenceItem` y `ConfidenceAssessment`.
7. `ReviewDecision` actúa sobre sujetos revisables; eventualmente existen `CanonicalEntity` + `Mapping`.
8. Audit/Lineage y el Information Graph (conceptual) enlazan el recorrido.

## Relacionados

- Arquitectura: [architecture.md](architecture.md)
- Terminología: [terminology.md](terminology.md)
- Seguridad: [security.md](security.md)
- ADR Fase 0.1: [decisions/0001-phase-0-1-domain-and-execution-model.md](decisions/0001-phase-0-1-domain-and-execution-model.md)
