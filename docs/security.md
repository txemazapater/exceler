# Seguridad

EXCELER trata información corporativa potencialmente sensible. La seguridad es un principio de diseño, no un añadido posterior.

## Solo lectura sobre orígenes

El descubrimiento y el análisis **no deben**:

- modificar archivos;
- renombrarlos, moverlos o eliminarlos;
- corregirlos ni guardar cambios;
- actualizar propiedades del origen;
- reorganizar carpetas;
- alterar permisos ACL/RBAC del origen.

Cualquier escritura sobre un origen se considera fuera de diseño, salvo que un ADR futuro lo autorice de forma explícita y acotada (hoy: no autorizado).

## Mínimo privilegio

- Identidades técnicas dedicadas, de solo lectura.
- Alcance limitado a las raíces y patrones necesarios.
- Capacidades del conector alineadas con lo mínimo para inventariar y leer.
- Separación entre cuentas de exploración y cuentas administrativas.

## Separación configuración / secretos

- La configuración de un origen guarda una **referencia de credencial**, no el secreto.
- Usuarios, contraseñas, tokens, certificados y cadenas de conexión secretas no viven en el modelo de origen.
- La abstracción debe permitir almacenes seguros (vault, secret manager, store del SO, etc.) sin fijar uno en Fase 0.

## Referencias de credencial

Una `CredentialReference` identifica:

- proveedor o almacén lógico;
- identificador del secreto;
- opcionalmente versión o política de rotación.

La resolución ocurre en tiempo de ejecución para el conector, con el menor tiempo de residencia en memoria posible.

## Auditoría

Debe poder reconstruirse:

- qué origen se exploró;
- cuándo;
- con qué identidad técnica (sin exponer el secreto);
- qué activos se leyeron;
- qué componente y versión realizó el análisis;
- qué inferencias se generaron;
- quién aprobó o rechazó propuestas.

Ver subsistema *Audit and Lineage* en [architecture.md](architecture.md).

## Datos sensibles

- Los libros pueden contener PII, datos financieros o información restringida.
- El perfilado y las muestras de evidencia deben minimizar retención de valores crudos.
- Los informes no deben filtrar secretos ni volcar columnas sensibles por defecto.
- Las futuras muestras del repositorio serán sintéticas; ver [samples/README.md](../samples/README.md).

## Copias temporales y limpieza

Si un conector necesita materializar un archivo temporal para analizarlo:

- usar ubicaciones controladas;
- restringir permisos locales;
- eliminar temporales al finalizar (éxito o error);
- no reutilizar temporales entre ejecuciones sin control;
- no dejar residuos en directorios compartidos.

## Protección de muestras

- Prohibido versionar datos corporativos reales.
- Las muestras de prueba deben ser ficticias y documentadas.
- Si se usan datos “realistas”, deben ser generados, no anonimizaciones dudosas de producción.

## Límites de acceso

Los orígenes deben soportar:

- raíces acotadas;
- include/exclude;
- límites de profundidad, número de archivos, tamaño y tiempo;
- omisión de rutas no autorizadas sin intentar elevar privilegios.

## Macros y contenido activo

- EXCELER puede **detectar** la presencia de macros u otro contenido activo.
- EXCELER **no debe ejecutar** macros, VBA, XLM ni código embebido durante el análisis.
- Los formatos con macros (p. ej. XLSM) se tratan como datos a inspeccionar, no como programas a lanzar.
- Cualquier dependencia de biblioteca debe configurarse para evitar ejecución automática de contenido activo cuando sea posible.

## Riesgos a vigilar

| Riesgo | Mitigación conceptual |
|--------|----------------------|
| Escritura accidental en origen | Contratos de conector solo lectura + pruebas de no mutación |
| Fuga de secretos en logs | Redacción; no loguear credenciales ni URLs con tokens |
| Retención excesiva de PII | Muestreo limitado; políticas de retención |
| Path traversal / escapes de raíz | Validación de rutas respecto a la raíz autorizada |
| Archivos maliciosos | No ejecutar macros; límites de tamaño; aislamiento de parsing |
| Inventario como canal de exfiltración | Controles de acceso al propio EXCELER y a informes |

## Relacionados

- Alcance: [scope.md](scope.md)
- Arquitectura: [architecture.md](architecture.md)
- Roadmap: [roadmap.md](roadmap.md)
