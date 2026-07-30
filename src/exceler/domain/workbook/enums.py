from __future__ import annotations

from enum import StrEnum


class WorkbookFormat(StrEnum):
    XLSX = "xlsx"
    XLSM = "xlsm"


class WorksheetVisibility(StrEnum):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    VERY_HIDDEN = "veryHidden"


class CellValueKind(StrEnum):
    NULL = "null"
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    ERROR = "error"


class InspectionCompletionStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"


class InspectionTruncationCode(StrEnum):
    MAX_CELLS_OBSERVED = "MAX_CELLS_OBSERVED"
    MAX_CELLS_SCANNED = "MAX_CELLS_SCANNED"
    MAX_WORKSHEETS = "MAX_WORKSHEETS"


class InspectionWarningCode(StrEnum):
    UNSUPPORTED_FEATURE = "UNSUPPORTED_FEATURE"
    EXTERNAL_LINK_PRESENT = "EXTERNAL_LINK_PRESENT"
    DIMENSION_MAY_BE_INFLATED = "DIMENSION_MAY_BE_INFLATED"
    VBA_PROJECT_PRESENT = "VBA_PROJECT_PRESENT"
    ENCRYPTED_WORKBOOK = "ENCRYPTED_WORKBOOK"
    CELL_LIMIT_REACHED = "CELL_LIMIT_REACHED"
    FORMULA_CACHE_UNAVAILABLE = "FORMULA_CACHE_UNAVAILABLE"
    WORKSHEET_LIMIT_REACHED = "WORKSHEET_LIMIT_REACHED"
    SOURCE_SIZE_CHANGED = "SOURCE_SIZE_CHANGED"
    MATERIALIZED_CELLS_FALLBACK = "MATERIALIZED_CELLS_FALLBACK"
