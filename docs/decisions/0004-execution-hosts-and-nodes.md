# ADR 0004 — Modelo de hosts y nodos de ejecución

- **Estado:** accepted
- **Fecha:** 2026-07-30
- **Decisores:** proyecto EXCELER
- **Relacionado:** [ADR 0002](0002-runtime-and-deployment-strategy.md)

## Contexto

Docker Compose es el entorno reproducible de referencia, pero EXCELER no debe asumir que todos los orígenes son accesibles desde un único servidor central. La evolución prevista incluye escritorio, agentes remotos y ejecución nativa.

## Decisión

Separar **EXCELER Core** (dominio, aplicación, contratos) de los **hosts** donde puede ejecutarse:

| Host | Rol |
|------|-----|
| **Server Host** | Compose/API/PostgreSQL; orígenes montados `:ro`; despliegue centralizado y coordinación futura |
| **Native Host** | CLI/servicio nativo Windows o Linux; desarrollo, depuración, automatización |
| **Desktop Host** | UI (p. ej. Electron) como cliente/orquestador local; **sin** lógica de dominio en el shell UI |
| **Agent Host** | Nodo ligero de descubrimiento/inspección local, con posible modo desconectado y sincronización posterior |

Implicaciones:

- la **configuración** de un origen puede ser válida aunque no sea **accesible** en el host actual;
- la accesibilidad es relativa al nodo que ejecuta la validación o el descubrimiento;
- Desktop y Agent no se implementan en esta iteración; quedan como hosts documentados.

## Alternativas consideradas

- **Solo Server Host** — simple; bloquea agentes y escritorio.
- **Asumir mounts globales** — incorrecto cuando el origen vive en otro nodo.

## Consecuencias

### Positivas

- Decisiones futuras de conectores/agentes no rehacen el modelo de validación.
- Compose permanece como referencia sin monopolizar el diseño.

### Negativas / riesgos

- Hay que disciplinar APIs y UX para no confundir “mal configurado” con “no montado aquí”.

## Referencias

- [architecture.md](../architecture.md)
- [deployment.md](../deployment.md)
- [ADR 0002](0002-runtime-and-deployment-strategy.md)
