# Changelog

Formato inspirado en [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- Fase 2D.7: compatibilidad solo entre entidades simples inequívocas; rechazo de
  solape parcial en encabezados compuestos (`CustomerProductId→CustomerId/ProductId`);
  razón `ambiguous_reference_target_semantics`.
- Fase 2D.6: compatibilidad semántica referencia↔destino (`ENTITY_ALIAS_GROUPS`);
  rechazo `ProductId→CustomerId`; aliases `ClientId`/`ArticleCode`; corpus
  `rel_incompatible_product_customer`, `rel_alias_*`, `rel_insufficient_bare_id_fk`.
- Fase 2D.5: evidencia de referencia en el hijo FK y límites de token en encabezados;
  rechazo `Sales.Amount → Customers.CustomerId` (`rel_measure_into_identifier_no_fk`)
  conservando `Orders.CustomerId → Customers.CustomerId`.
- Fase 2D.4: evidencia independiente vs soporte relacional; rechazo de medidas
  coincidentes (`rel_matching_measures_no_relation`); sin circularidad FK↔PK.
- Fase 2D.3: evidencia estructural para PKs numéricas (`fk_parent_reference`);
  escenario `rel_numeric_customer_id_fk`; Qty único accidental sigue rechazado.
- Fase 2D.2: calibración de confianza vs peso máximo, aceptación/rechazo explícito,
  sin SURROGATE automático por INTEGER único, corpus negativo/ranking
  (`rel_integer_unique_not_surrogate`, `rel_pk_ranking`).
- Fase 2D: claves y relaciones estructurales intra-workbook (`DeterministicRelationshipAnalyzer`,
  CLI `workbook relationships`, `expectations.relationships`, corpus `rel_*`).
- Documentación `docs/keys-and-relationships.md`.
- Fase 2C: perfilado e inferencia de tipos estructurales (`DeterministicRegionProfiler`, CLI
  `workbook profile`, `expectations.profiling`, corpus de tipos/anomalías/ids).
- Documentación `docs/profiling-and-type-inference.md`.

### Changed

- Relationship engine **2D.7**: multi-entity headers are ambiguous, not partially compatible.
- Relationship engine **2D.6**: FK acceptance requires reference-target semantic
  compatibility; declared aliases only; insufficient entity headers do not accept.
- Relationship engine **2D.5**: FK sources require child reference evidence; header
  identifier tokens use whole-token boundaries (no free `id$` suffix).
- Relationship engine **2D.4**: FK destination requires independent identifier evidence;
  relationship support cannot alone accept numeric PKs.
- Relationship engine **2D.3**: FK discovery before PK scoring; numeric acceptance
  gated on structural FK-parent evidence.
- Relationship engine **2D.2**: score/accepted separados; grafo solo con candidatos accepted.
- Roadmap: 2D = keys **and** relationships; inter-workbook diferido (antes “2E”).
- Profiler **2C.3**: matriz explícita DATE/DATETIME/TIME (un `09:30` ya no es
  compatible con DATE; DATE sí promociona a DATETIME).
- Profiler **2C.2**: parseo numérico sin locale fija, enteros/decimales como texto,
  `unique_ratio` = singletons/content, fechas ordenadas por valor parseado, compatibilidad
  centralizada para inferencia y anomalías.
- Fase 2B contrato endurecido (`regions_schema_version` 2 / detector `2B.2`): ocupación en capas
  (observed/content/visual) y tablas estructuradas que reservan su interior ante solapes parciales.
- Roadmap/README: siguiente corte **2D**.

### Changed

- Fase 2B marcada como cerrada; siguiente corte 2C.
- README/roadmap/limitations actualizados para regiones.

### Added (prev)

- Fase 2A hardening: identidad por `sha256(payload)`, `cells_scanned`/`cells_observed`, inspección `complete`/`partial`, schema JSON 2, exit CLI 7.
- Fixtures patológicos: `pathological_inflated_dimension`, `moderately_inflated_dimension`, `max_observed_cells_partial`.

### Changed (prev)

- Fase 2A marcada como cerrada tras hardening de límites e identidad.
- `WorkbookSource` ya no exige `content_hash()` en el protocolo.

### Added (earlier)

- Fase 2A: Workbook Inspection Foundation (`WorkbookInspection`, `OpenPyxlWorkbookReader`, CLI `workbook inspect`).
- Corpus 2A ampliado (tipos físicos, veryHidden, freeze/autofilter, VBA stub, dimensión inflada, tablas avanzadas, …).
- Documentación `docs/workbook-inspection.md`, `docs/limitations.md`, ADR 0005.
- Fase 2.0 endurecida / corpus sintético / verify CI.

## [0.0.0] — 2026-07-30

### Added

- Repositorio inicial con README de estado.
