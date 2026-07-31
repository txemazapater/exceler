# Keys and relationships (Phase 2D)

Análisis estructural de claves candidatas y relaciones intra-workbook a partir de:

```text
WorkbookInspection + RegionDetectionResult + ProfilingResult → RelationshipAnalysisResult
```

El analyzer **no** reabre Excel ni importa openpyxl/pandas.

## Flujo CLI

```bash
uv run exceler workbook relationships archivo.xlsx
uv run exceler workbook relationships archivo.xlsx --format json --pretty
```

Ejecuta inspect → regions → profile → relationships en una sola lectura de Excel.

## Contrato

- Dominio: `exceler.domain.relationships`
- Implementación: `DeterministicRelationshipAnalyzer`
- `relationship_schema_version` = **1**
- `relationship_engine_version` = **2D.3**
- Conserva versiones de inspector / detector / profiler / regions / profiling

Triple hash: `inspection.file.content_hash == regions.workbook_hash == profiling.workbook_hash`
(`RelationshipInputMismatchError` si no).

## Entradas y valor sets

1. Los conjuntos de valores para inclusión FK y unicidad compuesta se reconstruyen desde
   celdas de `WorkbookInspection` vía bbox − header/footer (mismo patrón que 2C).
2. **Nunca** se usan `sample` / `top_values` del perfil como conjuntos completos.
3. Profiling aporta evidencia de tipo, cardinalidad e identificador — no el dominio de valores.
4. Las fórmulas no aportan valor de clave (NULL) y generan warning.

## Salida

- `primary_keys` / `composite_keys` por hoja con `score`, `confidence`, `accepted`,
  `rejection_reasons` (candidatos, nunca “la” PK definitiva)
- `foreign_keys` y `relationships` con inclusión, cobertura, huérfanos y cardinalidad
- `graph` (nodos/aristas estructurales; solo candidatos **accepted**)
- evidencias (`RelationshipEvidenceItem`) y warnings/limitations

Composites: **pares** solamente (triples detrás de opción, default off).

## Confianza y aceptación (2D.2 / 2D.3)

1. `score`/`confidence` se normalizan contra el **peso positivo máximo posible**
   (`RelationshipOptions.max_*_positive_weight`), no contra la evidencia presente.
2. La aceptación es ortogonal al score: umbrales de distinct/null/score y tipos penalizados.
3. Candidatos rechazados pueden emitirse marcados (`accepted=false`) para inspección.
4. `INTEGER` + unicidad **no** implica `SURROGATE`; ese kind queda reservado a evidencia más fuerte.
5. Tipos `TEXT`/`BOOLEAN`/… penalizados se rechazan como PK aunque sean únicos.
6. `INTEGER`/`NUMBER`/`DECIMAL` únicos se rechazan **salvo** evidencia estructural adicional
   (p. ej. ser padre de un FK accepted → `fk_parent_reference`); tampoco se etiquetan `SURROGATE`.

## Decisiones

1. Sin señales de nombre de columna para ranking PK/FK (headers solo en salida humana).
2. Sin openpyxl/Excel/pandas en `domain.relationships` ni `application.relationships`.
3. MVP de un solo workbook; IDs de extremos permiten multi-workbook futuro.
4. Pesos de evidencia centralizados en `RelationshipOptions`.
5. Pares FK ambiguos: se conservan alternativas; no se fuerza un ganador.
6. Bridge N:M: ambas lados no únicos + inclusión mutua alta → `many_to_many` con confianza moderada.

## Escenarios de corpus

`rel_simple_primary_key`, `rel_duplicate_identifier`, `rel_composite_key`,
`rel_customers_orders`, `rel_invoice_header_lines`, `rel_orphan_and_partial`,
`rel_bridge_table`, `rel_integer_unique_not_surrogate`, `rel_numeric_customer_id_fk`,
`rel_pk_ranking` — expectativas parciales en `expectations.relationships`
(incluye negativos, ranking y numéricos con evidencia FK).

## Fuera de alcance

- Relaciones entre workbooks distintos (diferido; antes “2E” del roadmap legacy)
- Semántica de negocio / entidades nombradas
- Declaración automática de constraints definitivos
- Evaluación de fórmulas
