# Visión

## Problema empresarial

En muchas organizaciones, la información crítica no vive solo en sistemas formales. Vive en carpetas compartidas, unidades de red, bibliotecas documentales y copias locales de libros Excel.

Esos libros actúan como almacenes informales porque:

- permiten capturar datos sin pasar por un proyecto de IT;
- admiten reglas de negocio embebidas (fórmulas, validaciones, macros);
- se copian y adaptan con facilidad;
- se convierten en “fuente de verdad” de facto para un equipo o proceso.

El resultado típico es un mapa opaco: nadie sabe con certeza cuántos libros existen, qué entidades modelan, qué relaciones mantienen entre sí ni qué grado de divergencia hay respecto a los sistemas oficiales.

## Visión del producto

EXCELER debe convertirse en un **sistema de descubrimiento, inventario, análisis e inferencia** de almacenes informales de información, empezando por Excel.

Su misión no es sustituir de inmediato esos libros, sino:

1. hacerlos visibles;
2. hacerlos comprensibles;
3. proponer un modelo corporativo consolidable;
4. preservar el linaje entre origen, inferencia y decisión humana.

La transformación hacia una base de datos centralizada es un resultado asistido y validado, no un efecto colateral automático del descubrimiento.

## Roles potenciales

| Rol | Interés principal |
|-----|-------------------|
| Arquitecto / ingeniero de datos | Entender fuentes ocultas y preparar consolidación |
| Responsable de gobierno de datos | Inventario, calidad, trazabilidad y riesgos |
| Analista de negocio / dominio | Validar entidades, claves y significados |
| Seguridad / cumplimiento | Exposición de datos, privilegios mínimos, auditoría |
| Operaciones / IT | Orígenes, conectividad, ejecución de exploraciones |
| Dirección técnica | Alcance del shadow data y coste de consolidación |

La interfaz CRUD de usuario final no forma parte de la visión inmediata; la prioridad es el motor de descubrimiento y modelado.

## Valor esperado

- Reducir la incertidumbre sobre dónde está la información corporativa informal.
- Inventariar activos sin alterar las fuentes.
- Acelerar el diseño de esquemas consolidados con evidencia, no con intuición.
- Separar hechos observados de interpretaciones y de decisiones aprobadas.
- Facilitar revisiones humanas con confianza, advertencias y conflictos explícitos.

## Horizonte a largo plazo

Más allá de Excel, el núcleo conceptual debe poder incorporar otras fuentes (CSV, Access, SQLite, JSON, XML, bases de datos, APIs, plataformas documentales), manteniendo:

- descubrimiento y acceso desacoplados del análisis;
- tres capas de modelo (observado, inferido, canónico);
- trazabilidad y revisión humana;
- generación asistida de esquemas hacia destinos formales.

Eventualmente podrán existir CLI, servicio centralizado y agentes distribuidos. Esas formas de despliegue son consecuencias de la arquitectura, no su punto de partida.

## Límites actuales

En las Fases 0 / 0.1:

- no hay implementación ejecutable;
- no hay conectores reales;
- no hay interfaz de usuario;
- no hay migración automática;
- Excel es el primer tipo de documento previsto, no el único posible a largo plazo;
- el Information Graph existe como modelo conceptual; su navegación operativa es posterior.

Ver [scope.md](scope.md) y [roadmap.md](roadmap.md).
