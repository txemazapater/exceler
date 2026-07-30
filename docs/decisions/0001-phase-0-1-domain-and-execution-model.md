# ADR 0001 — Corrección del modelo temporal y de ejecución (Fase 0.1)

- **Estado:** accepted
- **Fecha:** 2026-07-30
- **Decisores:** proyecto EXCELER

## Contexto

La Fase 0 definió el dominio inicial, pero el modelo temporal y de ejecución quedaba incompleto para una implementación fiel:

- el análisis no distinguía con claridad la identidad durable del activo de la captura analizada;
- inspección, perfilado e inferencia no tenían ejecuciones propias;
- las relaciones candidatas no fijaban extremos;
- evidencia y confianza podían confundirse;
- la revisión parecía acoplada a mappings;
- ausencia en inventario y fallo de lectura podían mezclarse;
- el Information Graph parecía “aparecer” tarde en el roadmap;
- SMB y SharePoint/OneDrive quedaban demasiado diferidos respecto a su relevancia empresarial.

## Decisión

Antes de implementar:

1. Introducir `AssetSnapshot` como ancla del análisis reproducible.
2. Definir `InspectionRun`, `ProfilingRun` e `InferenceRun` además de `DiscoveryRun`.
3. Exigir extremos explícitos en `CandidateRelationship`.
4. Separar `EvidenceItem` y `ConfidenceAssessment`.
5. Generalizar `ReviewDecision` a cualquier sujeto revisable.
6. Tratar **presencia** y **accesibilidad** como dimensiones ortogonales.
7. Declarar el Information Graph como modelo conceptual desde el inicio; la fase posterior es navegación/materialización.
8. Adelantar conectores SMB y SharePoint/OneDrive en el roadmap (fases 4 y 5).

La documentación canónica queda en `docs/domain-model.md`, `docs/terminology.md`, `docs/architecture.md` y `docs/roadmap.md`.

## Alternativas consideradas

- **Implementar Fase 1–3 con el modelo 0.0 y corregir después** — más barato a corto plazo; caro en migraciones de esquema y semántica.
- **Un único `AnalysisRun` genérico** — simplifica nombres; mezcla responsabilidades y versiones de componentes.
- **Confianza como campo escalar en cada inferencia** — compacto; pierde método, versión y trazas de evidencias.
- **Mantener SPO/OneDrive “más allá”** — evita alcance temprano; aleja el producto de orígenes reales frecuentes.

## Consecuencias

### Positivas

- Inventario y análisis quedan temporalmente explícitos.
- Mejor trazabilidad y pruebas reproducibles vía snapshot.
- Revisión y grafo encajan con el resto del dominio sin remiendos tempranos.
- Roadmap de conectores alineado con entornos corporativos típicos.

### Negativas / riesgos

- Más entidades conceptuales antes del primer código.
- Hay que disciplinar a no implementar “atajos” que remezclan presencia/accesibilidad o evidencia/confianza.

### Seguimiento

- Fase 1 debe usar este modelo, no el de Fase 0 sin corregir.
- Los cambios que alteren la **semántica, responsabilidades o relaciones** del dominio requieren ADR o enmienda a este.
- Los **renombres editoriales** sin cambio semántico solo requieren actualización coherente de código y documentación (no un ADR nuevo).

## Referencias

- [domain-model.md](../domain-model.md)
- [terminology.md](../terminology.md)
- [architecture.md](../architecture.md)
- [roadmap.md](../roadmap.md)
