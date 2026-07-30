# ADR 0002 — Estrategia inicial de ejecución y despliegue

- **Estado:** accepted
- **Fecha:** 2026-07-30
- **Decisores:** proyecto EXCELER
- **Enmienda:** 2026-07-30 — hosts de ejecución (ver también ADR 0004)

## Contexto

EXCELER necesita un entorno reproducible para desarrollo y la primera implementación ejecutable (Fase 1), sin convertir Docker en dependencia del dominio ni adelantar microservicios, colas o orquestadores.

## Decisión

1. **Docker Compose** es el entorno reproducible de referencia para ejecutar la aplicación y su base de datos (**Server Host**).
2. La **ejecución nativa** (**Native Host**) permanece soportada para desarrollo, pruebas, CLI, depuración y futuros agentes.
3. La aplicación es inicialmente un **monolito modular** (`exceler-app`): API, aplicación, dominio, infraestructura y CLI en un mismo proceso de proceso.
4. **PostgreSQL** corre como servicio separado (`exceler-db`) en red interna Compose (detalle de stack en ADR 0003).
5. Los **orígenes** en Server Host se montan como volúmenes **`:ro`**; EXCELER registra rutas internas (p. ej. `/sources/...`). La autenticación SMB, si aplica, la gestiona el host en esta fase.
6. Los **secretos** se proporcionan externamente (env no versionado, archivos en `/run/secrets/`, referencias `env://` / `file://`); nunca en el repositorio.
7. La separación futura API/workers solo se introduce cuando exista una necesidad real de carga o aislamiento.
8. **EXCELER Core** es independiente del host. Además de Server y Native, se reconocen **Desktop Host** y **Agent Host** como modos futuros ([ADR 0004](0004-execution-hosts-and-nodes.md)). La accesibilidad de un origen es relativa al nodo que la evalúa.

Docker es vehículo de despliegue, no concepto de dominio ni el único modelo de distribución.

## Alternativas consideradas

- **Solo nativo** — más simple para un desarrollador; peor reproducibilidad entre máquinas.
- **Kubernetes desde el día 1** — sobredimensionado para Fase 1.
- **App + DB + Redis + MinIO + workers** — introduce piezas sin caso de uso actual.
- **SMB directo en el contenedor ya** — anticipa Fase 4; complica secretos y red.

## Consecuencias

### Positivas

- `docker compose up --build` reproduce el entorno Server Host.
- El dominio permanece agnóstico a contenedores.
- Orígenes acotados y de solo lectura vía mounts cuando el Server Host los materializa.

### Negativas / riesgos

- Los mounts dependen del host; hay que documentar rutas de ejemplo, no corporativas.
- `read_only: true` en el contenedor de app exige volúmenes/tmpfs explícitos para escritura.
- No todos los orígenes serán accesibles desde el servidor central.

### Seguimiento

- Documentar en `docs/deployment.md` y `docs/development.md`.
- Detalle de hosts en ADR 0004.
- No añadir herramientas admin de DB salvo necesidad justificada.

## Referencias

- [deployment.md](../deployment.md)
- [ADR 0003](0003-initial-technology-stack.md)
- [ADR 0004](0004-execution-hosts-and-nodes.md)
