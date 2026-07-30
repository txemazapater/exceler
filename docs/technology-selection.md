# Criterios de selección tecnológica

Este documento **no decide** el stack. Fija requisitos y criterios que condicionarán futuros ADR.

## Decisiones explícitamente abiertas

Todavía no se asume:

- lenguaje de programación;
- framework;
- base de datos de control/inventario;
- sistema de colas;
- motor de grafos;
- formato de configuración;
- plataforma de empaquetado/ejecución;
- interfaz de usuario.

Cualquier elección deberá registrarse en [decisions/](decisions/README.md).

## Requisitos que condicionan la elección

### Lectura de Excel

- Lectura robusta de **XLSX** y **XLSM**.
- Posible lectura futura de **XLS**.
- Análisis **sin ejecutar macros** ni contenido activo.
- Capacidad de inspeccionar estructura (hojas, tablas, nombres, fórmulas, vínculos) y, en fases posteriores, perfilar valores.
- Comportamiento predecible ante archivos grandes y parcialmente corruptos (fallar de forma controlada).

### Plataforma

- Funcionamiento en **Windows y Linux** como objetivo de diseño.
- Posibilidad de ejecución centralizada y, más adelante, distribuida (agentes).

### Arquitectura de software

- Conectores desacoplados del análisis.
- Extensibilidad a otros tipos de documento sin reescribir el núcleo.
- Soporte conceptual para CLI, servicio y agentes.
- Observabilidad básica (logs estructurados, correlación por `DiscoveryRun`).

### Datos y gobierno

- Trazabilidad completa (linaje).
- Separación observado / inferido / canónico.
- Referencias de credenciales hacia almacenes seguros.
- Pruebas reproducibles con muestras sintéticas.

### Operación

- Límites de tiempo, tamaño y cardinalidad configurables.
- Limpieza de temporales.
- Normalización de errores de conector.

## Criterios de evaluación (cuando llegue el momento)

| Criterio | Pregunta guía |
|----------|---------------|
| Adecuación a Excel | ¿Permite inspección sin ejecución de macros? |
| Rendimiento | ¿Soporta archivos grandes con muestreo controlado? |
| Portabilidad | ¿Windows + Linux sin bifurcaciones imposibles? |
| Seguridad | ¿Facilita secretos por referencia y mínimos privilegios? |
| Testabilidad | ¿Permite pruebas deterministas con fixtures sintéticas? |
| Operabilidad | ¿Logs, versiones de componente, fallos recuperables? |
| Complejidad | ¿La abstracción paga su coste en la fase actual? |
| Ecosistema | ¿Conectores FS/SMB/cloud son realistas después? |

## Anti-objetivos de esta fase

- Elegir tecnología por moda o por defecto del autor.
- Introducir dependencias “por si acaso”.
- Crear CI sin código que validar.
- Fijar UI antes de existir el motor.

## Próximo paso sugerido

Cuando se aborde la Fase 1–2, redactar ADR separados al menos para:

1. lenguaje/runtime;
2. persistencia del registro/inventario;
3. biblioteca de lectura Excel.

Hasta entonces, este documento es la referencia de requisitos.
