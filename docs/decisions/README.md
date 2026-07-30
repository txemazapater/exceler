# Architecture Decision Records (ADR)

Los ADR documentan decisiones arquitectónicas **reales**: contexto, elección, alternativas y consecuencias.

No se crean ADR ficticios ni proactivos “por completar la carpeta”.

## Cuándo escribir un ADR

- Se elige lenguaje, librería o persistencia.
- Se cambia un contrato entre subsistemas.
- Se altera el significado de una entidad de dominio.
- Se acepta una excepción a un principio (p. ej. solo lectura).
- Se descarta una alternativa relevante tras evaluarla.

## Convención de nombres

```text
NNNN-titulo-corto.md
```

Ejemplo: `0001-lenguaje-de-implementacion.md`

- `NNNN` es un entero creciente con ceros a la izquierda.
- El título es breve y en kebab-case.

## Estados

| Estado | Significado |
|--------|-------------|
| proposed | En discusión |
| accepted | Vigente |
| superseded | Reemplazado por otro ADR |
| deprecated | Ya no aplica |
| rejected | Evaluado y descartado |

## Plantilla

Copiar al crear un ADR nuevo:

```markdown
# ADR NNNN — Título

- **Estado:** proposed | accepted | superseded | deprecated | rejected
- **Fecha:** YYYY-MM-DD
- **Decisores:** (opcional)
- **Supersede/Superseded-by:** (opcional)

## Contexto

Qué problema o fuerza motiva la decisión. Incluir restricciones y requisitos relevantes.

## Decisión

Qué se decide hacer, en términos concretos.

## Alternativas consideradas

- Alternativa A — pros / contras
- Alternativa B — pros / contras

## Consecuencias

### Positivas

-

### Negativas / riesgos

-

### Seguimiento

Cambios documentales o técnicos derivados.

## Referencias

Enlaces a issues, PRs, docs de dominio/arquitectura, etc.
```

## Relación con el resto de la documentación

- Los ADR no sustituyen [architecture.md](../architecture.md); lo precisan.
- Si un ADR cambia vocabulario, actualizar [terminology.md](../terminology.md) y [domain-model.md](../domain-model.md).
- Registrar el impacto en [../CHANGELOG.md](../../CHANGELOG.md) cuando proceda.

## Índice

| ADR | Título | Estado |
|-----|--------|--------|
| [0001](0001-phase-0-1-domain-and-execution-model.md) | Corrección del modelo temporal y de ejecución (Fase 0.1) | accepted |
| [0002](0002-runtime-and-deployment-strategy.md) | Estrategia inicial de ejecución y despliegue | accepted |
| [0003](0003-initial-technology-stack.md) | Stack tecnológico inicial | accepted |
| [0004](0004-execution-hosts-and-nodes.md) | Modelo de hosts y nodos de ejecución | accepted |
