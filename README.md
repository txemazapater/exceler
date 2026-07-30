# EXCELER

**Exceler** — motor de descubrimiento de almacenes informales de información corporativa.

EXCELER aborda un problema habitual en empresas y organizaciones: la proliferación descontrolada de archivos Excel usados como bases de datos no gobernadas.

## El problema

Los libros Excel corporativos suelen acumular, sin diseño previo:

- datos maestros;
- registros operativos;
- catálogos y seguimientos;
- controles e históricos;
- reglas de negocio expresadas como fórmulas;
- relaciones implícitas con otros libros;
- copias parciales o divergentes de la misma información.

Excel acaba convirtiéndose en una base de datos informal porque es accesible, flexible y no exige modelado previo. El coste aparece después: duplicidad, inconsistencia, dependencia de personas concretas y dificultad para consolidar en sistemas formales.

## Qué pretende descubrir

EXCELER busca, de forma progresiva:

1. dónde están esos archivos;
2. cómo se accede a cada ubicación;
3. qué activos existen, sin modificar las fuentes;
4. cuál es su estructura y contenido observable;
5. qué entidades, campos, claves y relaciones candidatas se pueden inferir;
6. cómo construir un modelo de información corporativa;
7. qué esquemas consolidados podrían materializarse en una base de datos;
8. cómo mantener trazabilidad entre origen, inferencia y modelo aprobado.

## Fuera del alcance inicial

Quedan explícitamente fuera de esta fase:

- interfaz CRUD para usuario final;
- SPA (p. ej. Vue) u aplicación de escritorio;
- edición, corrección o migración automática de archivos origen;
- eliminación automática de duplicados;
- modificación de permisos en los orígenes.

## Principios fundamentales

1. **Descubrimiento antes que transformación** — observar, inventariar y comprender antes de materializar.
2. **Solo lectura sobre los orígenes** — no modificar, renombrar, mover ni eliminar archivos fuente.
3. **Separación entre acceso y análisis** — conectores, inspectores e inferencia no se mezclan.
4. **Trazabilidad completa** — toda inferencia debe poder rastrearse hasta su origen.
5. **Inferencias, no afirmaciones absolutas** — candidatos con evidencia, confianza y estado de revisión.
6. **Seguridad y mínimo privilegio** — credenciales por referencia; identidades técnicas de solo lectura.
7. **Arquitectura evolutiva** — Excel primero, sin acoplar el núcleo a un único formato.

Detalle en [docs/vision.md](docs/vision.md), [docs/scope.md](docs/scope.md) y [docs/security.md](docs/security.md).

## Estado del proyecto

El proyecto se encuentra en **fase de definición arquitectónica** (Fase 0).

Todavía no hay implementación de conectores, inventarios ni analizadores. El repositorio contiene la visión, el dominio, la arquitectura conceptual y el roadmap incremental.

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [docs/vision.md](docs/vision.md) | Problema, visión, roles y valor |
| [docs/scope.md](docs/scope.md) | Alcance, fuera de alcance, supuestos |
| [docs/architecture.md](docs/architecture.md) | Subsistemas y contratos conceptuales |
| [docs/domain-model.md](docs/domain-model.md) | Entidades conceptuales y relaciones |
| [docs/terminology.md](docs/terminology.md) | Glosario del dominio |
| [docs/security.md](docs/security.md) | Principios de seguridad y solo lectura |
| [docs/roadmap.md](docs/roadmap.md) | Roadmap por fases |
| [docs/technology-selection.md](docs/technology-selection.md) | Criterios de selección tecnológica (sin decisiones fijadas) |
| [docs/decisions/](docs/decisions/README.md) | Architecture Decision Records (ADR) |
| [samples/README.md](samples/README.md) | Criterios para muestras sintéticas de prueba |

## Estructura del repositorio

```text
/
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── docs/
│   ├── vision.md
│   ├── scope.md
│   ├── architecture.md
│   ├── domain-model.md
│   ├── terminology.md
│   ├── security.md
│   ├── roadmap.md
│   ├── technology-selection.md
│   └── decisions/
└── samples/
```

Las carpetas `src/`, `tests/`, `tools/` y `.github/` se añadirán cuando exista código real que organizar o validar.

## Licencia

Pendiente de decisión. No se ha fijado licencia todavía.

## Contribución

Ver [CONTRIBUTING.md](CONTRIBUTING.md).
