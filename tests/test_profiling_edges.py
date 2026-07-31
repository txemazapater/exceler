"""Unit tests for Phase 2C.2 profiling edge hardening."""

from __future__ import annotations

from exceler.application.profiling.compatibility import (
    CompatibilityStatus,
    check_compatibility,
)
from exceler.application.profiling.normalization import NormalizedValue
from exceler.application.profiling.numeric_parse import (
    NumericKind,
    infer_decimal_separator,
    parse_numeric_text,
)
from exceler.application.profiling.statistics import build_column_statistics
from exceler.application.profiling.temporal_parse import parse_temporal_text
from exceler.domain.profiling.enums import LogicalValueType
from exceler.domain.profiling.options import ProfilingOptions
from exceler.domain.workbook.enums import CellValueKind

pytestmark = __import__("pytest").mark.unit


def _nv(
    text: str | None,
    *,
    kind: CellValueKind = CellValueKind.STRING,
    number_format: str | None = None,
) -> NormalizedValue:
    if text is None:
        return NormalizedValue(
            original=None,
            trimmed=None,
            kind=CellValueKind.NULL,
            is_null=True,
            is_blank_string=False,
            is_whitespace_only=False,
            is_formula=False,
            is_error=False,
            has_content=False,
            coordinate="A1",
            number_format=number_format,
        )
    trimmed = text.strip()
    return NormalizedValue(
        original=text,
        trimmed=trimmed,
        kind=kind,
        is_null=False,
        is_blank_string=text == "",
        is_whitespace_only=bool(text and trimmed == ""),
        is_formula=False,
        is_error=False,
        has_content=bool(trimmed),
        coordinate="A1",
        number_format=number_format,
    )


def test_ambiguous_thousand_or_decimal_not_forced() -> None:
    assert parse_numeric_text("1.234").ambiguous
    assert parse_numeric_text("1,234").ambiguous
    assert parse_numeric_text("1.234").value is None


def test_unambiguous_decimal_and_european_fraction() -> None:
    us = parse_numeric_text("12.5")
    assert (
        us.ok
        and us.kind is NumericKind.DECIMAL
        and us.value == __import__("decimal").Decimal("12.5")
    )
    eu = parse_numeric_text("12,5")
    assert eu.ok and eu.value == __import__("decimal").Decimal("12.5")


def test_both_separators_uses_last_as_decimal() -> None:
    eu = parse_numeric_text("1.234,56")
    assert eu.ok and str(eu.value) == "1234.56"
    us = parse_numeric_text("1,234.56")
    assert us.ok and str(us.value) == "1234.56"


def test_column_consensus_resolves_ambiguous_group() -> None:
    assert infer_decimal_separator(["12.5", "3.25", "1.234"]) == "."
    resolved = parse_numeric_text("1.234", decimal_separator=".")
    assert resolved.ok and str(resolved.value) == "1.234"


def test_leading_zeroes_not_integer() -> None:
    parsed = parse_numeric_text("00045")
    assert not parsed.ok
    assert parsed.reason == "leading_zeroes"


def test_textual_integer_compatible() -> None:
    item = _nv("42")
    result = check_compatibility(item, LogicalValueType.INTEGER)
    assert result.status is CompatibilityStatus.COMPATIBLE


def test_unique_ratio_is_singletons_over_content() -> None:
    values = [
        _nv("A"),
        _nv("A"),
        _nv("B"),
        _nv("C"),
    ]
    stats, _ = build_column_statistics(
        values,
        options=ProfilingOptions(),
        observed_count=4,
        unobserved_count=0,
    )
    # distinct=3, content=4, singletons=2 (B,C)
    assert stats.distinct_count == 3
    assert stats.distinct_ratio == 0.75
    assert stats.unique_count == 2
    assert stats.unique_ratio == 0.5


def test_temporal_order_uses_parsed_values_not_lexicographic() -> None:
    # Lexicographic would put 03/04 before 2026-01-01; parsed ISO orders correctly.
    early = parse_temporal_text("2026-01-01")
    late = parse_temporal_text("2026-12-31")
    assert early.ok and late.ok
    assert early.sort_key < late.sort_key
    ambiguous = parse_temporal_text("03/04/2026")
    assert ambiguous.ambiguous
    assert ambiguous.sort_key is None


def test_compatibility_shared_for_date_mismatch() -> None:
    bad = _nv("error")
    result = check_compatibility(bad, LogicalValueType.DATE)
    assert result.status is CompatibilityStatus.INCOMPATIBLE
