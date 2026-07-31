# Limitaciones conocidas

## Workbook inspection (Phase 2A) — cerrada

- **`.xls` binario:** no soportado; decisión futura por ADR.
- **Propiedades de documento / personalizadas:** no son contrato de 2A.
- **Valores cacheados de fórmulas:** no se leen en 2A; haría falta una pasada `data_only=True` explícita y separada.
- **Enlaces externos:** se listan si openpyxl los expone; no hay fixture corporativo de enlace externo versionado.
- **Workbooks cifrados:** el error `ENCRYPTED_WORKBOOK` está preparado; no hay fixture cifrado portable versionado.
- **`vbaProject.bin` sintético:** `xlsm_with_vba_stub.xlsm` inyecta un stub no ejecutable solo para detectar presencia.
- **Nombres definidos locales (`localSheetId`):** openpyxl no los re-serializa de forma fiable al guardar; el corpus cubre nombres globales.
- **Dimensiones infladas:** `DIMENSION_MAY_BE_INFLATED` es heurística factual; el fallback patológico usa `worksheet._cells` **solo** dentro de `OpenPyxlWorkbookReader` (API interna de openpyxl encapsulada; ver ADR 0005 / workbook-inspection.md). No es detector de regiones.
- **Identidad:** el hash de inspección es siempre `sha256(payload)` de la captura binaria única; `LocalWorkbookSource.content_hash()` existe como utilidad y **no** forma parte del protocolo ni se usa en `inspect`.
- **openpyxl** es el único adaptador de lectura Excel en 2A (dependencia de producción).
- **Estilos (schema 3):** se exponen señales factuales (nombre/tamaño/negrita/color de fuente, fill, alineación horizontal, presencia de bordes). Colores theme/indexed se tokenizan; no se resuelve la paleta del tema a RGB final.

## Region detection (Phase 2B) — cerrada

- Tipos de región son etiquetas estructurales preliminares, no semántica de negocio.
- Geometría de charts/imágenes y caches de pivots quedan fuera del MVP.
- El detector solo consume `WorkbookInspection`; nunca relee el archivo.
- Huecos vacíos interiores se fusionan solo con score de continuidad (bordes/fill); gaps fuertes o bandas título↔tabla no se unen.
- **Ocupación en capas:** `observed` ≠ `content` ≠ `visual`; la densidad contractual usa contenido.
- **Tablas estructuradas:** reservan su interior; la heurística no compite dentro del ref Excel.

## Profiling (Phase 2C) — MVP

- Tipos lógicos son estructurales, no entidades de negocio.
- Las fórmulas se cuentan sin evaluar; no hay valores cacheados de 2A.
- Fechas ambiguas (DD/MM vs MM/DD) bajan confianza en lugar de imponer locale.
- DATE/DATETIME/TIME no se cruzan libremente: TIME no satisface DATE; DATETIME no satisface TIME;
  DATE sí promociona hacia DATETIME.
- Separadores numéricos ambiguos (`1.234` / `1,234`) no se convierten sin consenso de columna.
- Identifier/categorical son candidatos, no claves/FK definitivas.
- El profiler no relee Excel ni importa openpyxl.
- `unique_ratio` mide singletons/content; la unicidad de identificador usa `distinct_ratio`.

## Keys & relationships (Phase 2D) — MVP (2D.3)

- Claves y relaciones son **candidatos estructurales**, no constraints definitivos.
- Solo intra-workbook; relaciones entre libros quedan fuera de 2D.3.
- Sin ranking por nombre de columna; headers son etiquetas humanas.
- Fórmulas no aportan dominio de clave (sin evaluación).
- Sets truncados (`max_distinct_values_tracked`) degradan inclusión/confianza.
- Composites: pares solamente (triples opt-in, default off).
- Confianza calibrada contra peso máximo posible; aceptación separada del score.
- `INTEGER` único no se etiqueta automáticamente como `SURROGATE`.
- Tipos lógicos penalizados (p. ej. TEXT) se rechazan como PK aunque sean únicos.
- Numéricos únicos sin evidencia estructural (p. ej. Qty) se rechazan; con evidencia
  de padre FK pueden aceptarse como `primary` (2D.3).
- El analyzer consume solo inspection + regions + profiling; no relee Excel.
