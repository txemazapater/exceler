"""Profiling enums (Phase 2C) — structural types only, not business entities."""

from __future__ import annotations

from enum import StrEnum


class LogicalValueType(StrEnum):
    UNKNOWN = "unknown"
    EMPTY = "empty"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    DECIMAL = "decimal"
    NUMBER = "number"
    TEXT = "text"
    CODE = "code"
    IDENTIFIER = "identifier"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    PERCENTAGE = "percentage"
    CURRENCY = "currency"
    EMAIL = "email"
    URL = "url"
    PHONE = "phone"
    POSTAL_CODE = "postal_code"
    UUID = "uuid"


class ProfilingStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    INSUFFICIENT_DATA = "insufficient_data"


class StatisticExactness(StrEnum):
    EXACT = "exact"
    ESTIMATED = "estimated"
    TRUNCATED = "truncated"


class AnomalyType(StrEnum):
    TYPE_MISMATCH = "type_mismatch"
    FORMAT_MISMATCH = "format_mismatch"
    AMBIGUOUS_VALUE = "ambiguous_value"
    OUTLIER_LENGTH = "outlier_length"
    OUTLIER_SCALE = "outlier_scale"
    PARSE_FAILURE = "parse_failure"
    EXCEL_ERROR = "excel_error"


class AnomalySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
