"""Centralized logical-type compatibility checks (inference + anomalies)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from exceler.application.profiling.normalization import (
    NormalizedValue,
    has_currency_signal,
    has_leading_zeroes,
    has_percentage_format,
    looks_code,
    looks_email,
    looks_percentage_text,
    looks_phone,
    looks_postal,
    looks_url,
    looks_uuid,
)
from exceler.application.profiling.numeric_parse import NumericKind, parse_numeric_text
from exceler.application.profiling.temporal_parse import (
    TemporalKind,
    parse_temporal_text,
    temporal_kind_compatible,
)
from exceler.domain.profiling.enums import AnomalySeverity, AnomalyType, LogicalValueType
from exceler.domain.workbook.enums import CellValueKind


class CompatibilityStatus(StrEnum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    AMBIGUOUS = "ambiguous"
    SKIP = "skip"


@dataclass(frozen=True)
class CompatibilityResult:
    status: CompatibilityStatus
    anomaly_type: AnomalyType | None = None
    message: str | None = None
    severity: AnomalySeverity = AnomalySeverity.WARNING


def _numeric_as(
    item: NormalizedValue,
    *,
    want: NumericKind | None = None,
    decimal_separator: str | None = None,
) -> CompatibilityResult:
    if item.kind is CellValueKind.INTEGER:
        if want is NumericKind.DECIMAL:
            return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
        return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
    if item.kind is CellValueKind.DECIMAL:
        if want is NumericKind.INTEGER:
            # Exact integers stored as decimal are acceptable for NUMBER, not INTEGER.
            text = item.trimmed or item.original or ""
            parsed = parse_numeric_text(text, decimal_separator=decimal_separator)
            if (
                parsed.ok
                and parsed.value is not None
                and parsed.value == parsed.value.to_integral()
            ):
                return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
            return CompatibilityResult(
                CompatibilityStatus.INCOMPATIBLE,
                AnomalyType.TYPE_MISMATCH,
                "Decimal value incompatible with integer",
            )
        return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
    if item.kind is CellValueKind.STRING and item.trimmed:
        if has_leading_zeroes(item.trimmed) and want is NumericKind.INTEGER:
            return CompatibilityResult(
                CompatibilityStatus.INCOMPATIBLE,
                AnomalyType.TYPE_MISMATCH,
                "Leading zeroes are not plain integers",
            )
        parsed = parse_numeric_text(item.trimmed, decimal_separator=decimal_separator)
        if parsed.ambiguous:
            return CompatibilityResult(
                CompatibilityStatus.AMBIGUOUS,
                AnomalyType.AMBIGUOUS_VALUE,
                "Ambiguous numeric separators",
            )
        if not parsed.ok:
            return CompatibilityResult(
                CompatibilityStatus.INCOMPATIBLE,
                AnomalyType.TYPE_MISMATCH,
                "Value is not numeric",
            )
        if want is NumericKind.INTEGER and parsed.kind is not NumericKind.INTEGER:
            return CompatibilityResult(
                CompatibilityStatus.INCOMPATIBLE,
                AnomalyType.TYPE_MISMATCH,
                "Non-integer numeric text",
            )
        return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
    return CompatibilityResult(
        CompatibilityStatus.INCOMPATIBLE,
        AnomalyType.TYPE_MISMATCH,
        "Value incompatible with numeric type",
    )


def check_compatibility(
    item: NormalizedValue,
    selected: LogicalValueType,
    *,
    decimal_separator: str | None = None,
) -> CompatibilityResult:
    """Return whether ``item`` is compatible with the selected logical type."""
    if item.is_formula:
        return CompatibilityResult(CompatibilityStatus.SKIP)
    if item.is_error:
        return CompatibilityResult(
            CompatibilityStatus.INCOMPATIBLE,
            AnomalyType.EXCEL_ERROR,
            "Excel error value",
            AnomalySeverity.ERROR,
        )
    if not item.has_content:
        return CompatibilityResult(CompatibilityStatus.SKIP)

    text = item.trimmed or item.original or ""

    if selected is LogicalValueType.INTEGER:
        return _numeric_as(item, want=NumericKind.INTEGER, decimal_separator=decimal_separator)
    if selected is LogicalValueType.DECIMAL:
        return _numeric_as(item, want=NumericKind.DECIMAL, decimal_separator=decimal_separator)
    if selected is LogicalValueType.NUMBER:
        return _numeric_as(item, want=None, decimal_separator=decimal_separator)
    if selected is LogicalValueType.PERCENTAGE:
        if has_percentage_format(item.number_format) or looks_percentage_text(text):
            return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
        numeric = _numeric_as(item, want=None, decimal_separator=decimal_separator)
        if numeric.status is CompatibilityStatus.COMPATIBLE:
            return numeric
        return CompatibilityResult(
            CompatibilityStatus.INCOMPATIBLE,
            AnomalyType.TYPE_MISMATCH,
            "Value incompatible with percentage",
        )
    if selected is LogicalValueType.CURRENCY:
        if has_currency_signal(item.original, item.number_format):
            return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
        return _numeric_as(item, want=None, decimal_separator=decimal_separator)

    if selected is LogicalValueType.BOOLEAN:
        if item.kind is CellValueKind.BOOLEAN:
            return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
        if text.casefold() in {"true", "false", "0", "1", "yes", "no", "si", "sí"}:
            return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
        return CompatibilityResult(
            CompatibilityStatus.INCOMPATIBLE,
            AnomalyType.TYPE_MISMATCH,
            "Value incompatible with boolean",
        )

    if selected in {LogicalValueType.DATE, LogicalValueType.DATETIME, LogicalValueType.TIME}:
        selected_kind = {
            LogicalValueType.DATE: TemporalKind.DATE,
            LogicalValueType.DATETIME: TemporalKind.DATETIME,
            LogicalValueType.TIME: TemporalKind.TIME,
        }[selected]

        physical_kind: TemporalKind | None = None
        if item.kind is CellValueKind.DATE:
            physical_kind = TemporalKind.DATE
        elif item.kind is CellValueKind.DATETIME:
            physical_kind = TemporalKind.DATETIME
        elif item.kind is CellValueKind.TIME:
            physical_kind = TemporalKind.TIME

        if physical_kind is not None:
            if temporal_kind_compatible(selected_kind, physical_kind):
                return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
            return CompatibilityResult(
                CompatibilityStatus.INCOMPATIBLE,
                AnomalyType.TYPE_MISMATCH,
                f"Physical {physical_kind.value} incompatible with {selected.value}",
            )

        parsed = parse_temporal_text(text)
        if parsed.ambiguous:
            return CompatibilityResult(
                CompatibilityStatus.AMBIGUOUS,
                AnomalyType.AMBIGUOUS_VALUE,
                "Ambiguous date ordering",
            )
        if parsed.ok and parsed.kind is not None:
            if temporal_kind_compatible(selected_kind, parsed.kind):
                return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
            return CompatibilityResult(
                CompatibilityStatus.INCOMPATIBLE,
                AnomalyType.TYPE_MISMATCH,
                f"Parsed {parsed.kind.value} incompatible with {selected.value}",
            )
        return CompatibilityResult(
            CompatibilityStatus.INCOMPATIBLE,
            AnomalyType.TYPE_MISMATCH,
            f"Value incompatible with {selected.value}",
        )

    if selected is LogicalValueType.UUID:
        if looks_uuid(text):
            return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
        return CompatibilityResult(
            CompatibilityStatus.INCOMPATIBLE,
            AnomalyType.TYPE_MISMATCH,
            "Value incompatible with uuid",
        )
    if selected is LogicalValueType.EMAIL:
        if looks_email(text):
            return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
        return CompatibilityResult(
            CompatibilityStatus.INCOMPATIBLE,
            AnomalyType.TYPE_MISMATCH,
            "Value incompatible with email",
        )
    if selected is LogicalValueType.URL:
        if looks_url(text):
            return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
        return CompatibilityResult(
            CompatibilityStatus.INCOMPATIBLE,
            AnomalyType.TYPE_MISMATCH,
            "Value incompatible with url",
        )
    if selected is LogicalValueType.PHONE:
        if looks_phone(text):
            return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
        return CompatibilityResult(
            CompatibilityStatus.INCOMPATIBLE,
            AnomalyType.TYPE_MISMATCH,
            "Value incompatible with phone",
        )
    if selected is LogicalValueType.POSTAL_CODE:
        if looks_postal(text):
            return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
        return CompatibilityResult(
            CompatibilityStatus.INCOMPATIBLE,
            AnomalyType.TYPE_MISMATCH,
            "Value incompatible with postal_code",
        )
    if selected is LogicalValueType.CODE:
        if looks_code(text) or has_leading_zeroes(text):
            return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
        if item.kind is CellValueKind.STRING and text and " " not in text and len(text) <= 32:
            return CompatibilityResult(CompatibilityStatus.COMPATIBLE)
        return CompatibilityResult(
            CompatibilityStatus.INCOMPATIBLE,
            AnomalyType.TYPE_MISMATCH,
            "Value incompatible with code",
        )
    if selected in {
        LogicalValueType.TEXT,
        LogicalValueType.IDENTIFIER,
        LogicalValueType.UNKNOWN,
        LogicalValueType.EMPTY,
    }:
        return CompatibilityResult(CompatibilityStatus.COMPATIBLE)

    return CompatibilityResult(CompatibilityStatus.COMPATIBLE)


def is_incompatible(
    item: NormalizedValue,
    selected: LogicalValueType,
    *,
    decimal_separator: str | None = None,
) -> bool:
    result = check_compatibility(item, selected, decimal_separator=decimal_separator)
    return result.status is CompatibilityStatus.INCOMPATIBLE
