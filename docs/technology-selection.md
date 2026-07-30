# Criterios de selección tecnológica

Los criterios siguientes condicionaron los ADR 0002 y 0003. Las decisiones tomadas están en:

- [ADR 0002 — Ejecución y despliegue](decisions/0002-runtime-and-deployment-strategy.md)
- [ADR 0003 — Stack inicial](decisions/0003-initial-technology-stack.md)

## Decisiones abiertas (posteriores)

Todavía no se fija:

- biblioteca concreta de lectura Excel (Fase 6);
- sistema de colas / workers;
- motor de grafos;
- autenticación de producto;
- interfaz de usuario.

## Requisitos que condicionan la elección

### Lectura de Excel (futuro cercano)

- Lectura robusta de **XLSX** y **XLSM** sin ejecutar macros.
- Posible lectura futura de **XLS**.
- Fallo controlado ante archivos grandes o corruptos.

### Plataforma

- Windows y Linux.
- Contenerización sencilla; ejecución nativa para CLI/agentes.

### Arquitectura

- Conectores desacoplados del análisis.
- API + CLI + futuros workers sobre la misma capa de aplicación.
- Observabilidad básica (logs estructurados).

### Datos y gobierno

- Trazabilidad; secretos por referencia; pruebas con fixtures sintéticas.

## Criterios de evaluación

| Criterio | Pregunta guía |
|----------|---------------|
| Adecuación a Excel | ¿Permite inspección sin ejecución de macros? |
| Rendimiento | ¿Soporta archivos grandes con muestreo controlado? |
| Portabilidad | ¿Windows + Linux sin bifurcaciones imposibles? |
| Seguridad | ¿Facilita secretos por referencia y mínimos privilegios? |
| Testabilidad | ¿Pruebas deterministas con fixtures sintéticas? |
| Operabilidad | ¿Logs, versiones, fallos recuperables? |
| Complejidad | ¿La abstracción paga su coste en la fase actual? |
| Ecosistema | ¿Conectores FS/SMB/cloud son realistas después? |

## Selección actual (resumen)

| Área | Elección |
|------|----------|
| Lenguaje | Python 3.12+ |
| API | FastAPI |
| ORM / migraciones | SQLAlchemy 2 + Alembic |
| DB | PostgreSQL 16 |
| CLI | Typer |
| Despliegue de referencia | Docker Compose |

## Anti-objetivos actuales

- Microservicios, Redis, MinIO, Kubernetes, motor de grafos “por si acaso”.
- UI de producto antes del motor.
- CI decorativo sin valor (se añadirá cuando estabilice el pipeline de pruebas).
