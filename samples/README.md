# Muestras sintéticas

Esta carpeta documenta **cómo** construir libros de prueba. No contiene archivos corporativos reales.

Cuando existan fixtures versionables, se organizarán de forma similar a:

```text
samples/
├── README.md          ← este archivo
├── workbooks/         ← libros sintéticos (.xlsx / .xlsm de prueba)
└── expected/          ← resultados esperados de inspección/inferencia
```

`workbooks/` y `expected/` se crearán al iniciar las fases de inspección/pruebas, no antes.

## Reglas de privacidad

- Prohibido añadir datos de clientes, empleados o sistemas reales.
- Usar nombres, NIFs, cuentas y direcciones **ficticios**.
- No “anonimizar” exports de producción para colarlos como muestra.
- Si una muestra simula datos sensibles, debe etiquetarse como tal en su descripción.

## Casos de prueba previstos

Las futuras muestras deberían cubrir al menos:

| Caso | Qué ejercita |
|------|----------------|
| Tabla limpia | Caso base de región/campos |
| Encabezados desplazados | Detección de región no anclada en A1 |
| Varias tablas en una hoja | Segmentación de regiones |
| Celdas combinadas | Estructura irregular |
| Fórmulas | Observación sin evaluar efectos laterales peligrosos |
| Columnas mixtas | Perfilado de tipos aparentes |
| Claves duplicadas | Evidencia contra unicidad |
| Relaciones entre libros | Inferencia inter-archivo |
| Enlaces externos | Vínculos y linaje probable |
| Hojas ocultas | Visibilidad y cobertura |
| Nombres definidos | Rangos nombrados |
| Macros detectables | Detección **sin ejecución** (p. ej. XLSM sintético) |
| Formatos inconsistentes | Fechas/números como texto, etc. |
| Filas de totales | Ruido al inferir entidades |
| Notas y comentarios | Metadatos no tabulares |
| Datos sensibles ficticios | Redacción / políticas de muestreo |

## Metadatos recomendados por muestra

Cada workbook sintético debería acompañarse de una nota breve (en `expected/` o README local) con:

- propósito del caso;
- hojas relevantes;
- regiones esperadas;
- trampas deliberadas;
- si contiene macros (y confirmación de que son inocuas / no se ejecutan en tests).

## Relación con el roadmap

- Fase 0: solo esta guía.
- Fase 4+: añadir `workbooks/` mínimos para el inspector.
- Fase 5–6+: ampliar `expected/` con perfiles e inferencias de referencia.

Ver [docs/roadmap.md](../docs/roadmap.md) y [docs/security.md](../docs/security.md).
