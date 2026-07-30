# Limitaciones conocidas

## Workbook inspection (Phase 2A)

- **`.xls` binario:** no soportado; decisión futura por ADR.
- **Propiedades de documento / personalizadas:** no son contrato de 2A (openpyxl las expone de forma uneven entre versiones).
- **Valores cacheados de fórmulas:** no se leen en 2A; haría falta una pasada `data_only=True` explícita y separada.
- **Enlaces externos:** se listan si openpyxl los expone; no hay fixture corporativo de enlace externo versionado todavía.
- **Workbooks cifrados:** el error `ENCRYPTED_WORKBOOK` está preparado; no hay fixture cifrado portable versionado.
- **`vbaProject.bin` sintético:** `xlsm_with_vba_stub.xlsm` inyecta un stub no ejecutable solo para detectar presencia. No es un proyecto VBA real de Excel.
- **Dimensiones infladas:** la advertencia `DIMENSION_MAY_BE_INFLATED` es heurística factual (declared span vs celdas con valor), no detección de regiones.
- **Nombres definidos locales (`localSheetId`):** openpyxl no los re-serializa de forma fiable al guardar; el corpus 2A cubre nombres globales (rango y constante).
