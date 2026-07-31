"""Column statistics builders for Phase 2C."""

from __future__ import annotations

import statistics
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation

from exceler.application.profiling.normalization import (
    NormalizedValue,
    abstract_pattern,
)
from exceler.application.profiling.numeric_parse import (
    infer_decimal_separator,
    parse_numeric_text,
)
from exceler.application.profiling.temporal_parse import parse_temporal_value
from exceler.domain.profiling.enums import StatisticExactness
from exceler.domain.profiling.models import (
    ColumnStatistics,
    KindCount,
    NumericStatistics,
    TemporalStatistics,
    TextStatistics,
)
from exceler.domain.profiling.options import ProfilingOptions
from exceler.domain.workbook.enums import CellValueKind


def build_physical_distribution(
    values: list[NormalizedValue],
) -> dict[str, KindCount]:
    total = max(len(values), 1)
    counts: Counter[str] = Counter()
    for item in values:
        if item.is_formula:
            counts["formula"] += 1
        elif item.is_error:
            counts[CellValueKind.ERROR.value] += 1
        else:
            counts[item.kind.value] += 1
    return {
        key: KindCount(count=count, ratio=count / total)
        for key, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    }


def _median(nums: list[float]) -> float | None:
    if not nums:
        return None
    return float(statistics.median(nums))


def _text_stats(values: list[NormalizedValue]) -> TextStatistics | None:
    texts = [
        item.original
        for item in values
        if item.kind is CellValueKind.STRING and item.original is not None
    ]
    if not texts:
        return None
    lengths = [len(text) for text in texts]
    patterns = Counter(abstract_pattern(text) for text in texts)
    dominant = tuple(pattern for pattern, _ in patterns.most_common(5))
    return TextStatistics(
        min_length=min(lengths),
        max_length=max(lengths),
        average_length=sum(lengths) / len(lengths),
        median_length=_median([float(x) for x in lengths]),
        empty_string_count=sum(1 for item in values if item.is_blank_string),
        whitespace_only_count=sum(1 for item in values if item.is_whitespace_only),
        multiline_count=sum(1 for text in texts if "\n" in text or "\r" in text),
        dominant_patterns=dominant,
    )


def _physical_decimal(item: NormalizedValue) -> Decimal | None:
    if item.original is None:
        return None
    try:
        return Decimal(item.original)
    except InvalidOperation:
        return None


def _to_decimal(item: NormalizedValue, *, decimal_separator: str | None) -> Decimal | None:
    if item.kind is CellValueKind.INTEGER:
        return _physical_decimal(item)
    if item.kind is CellValueKind.DECIMAL:
        return _physical_decimal(item)
    if item.kind is CellValueKind.STRING and item.trimmed:
        parsed = parse_numeric_text(item.trimmed, decimal_separator=decimal_separator)
        if parsed.ok:
            return parsed.value
        return None
    return None


def _numeric_stats(values: list[NormalizedValue]) -> NumericStatistics | None:
    string_texts = [
        item.trimmed
        for item in values
        if item.kind is CellValueKind.STRING and item.trimmed and item.has_content
    ]
    decimal_separator = infer_decimal_separator([text for text in string_texts if text])

    nums: list[Decimal] = []
    excluded = 0
    candidates = [
        item
        for item in values
        if item.kind in {CellValueKind.INTEGER, CellValueKind.DECIMAL, CellValueKind.STRING}
        and item.has_content
    ]
    for item in candidates:
        parsed = _to_decimal(item, decimal_separator=decimal_separator)
        if parsed is None:
            # Ambiguous locale forms are excluded, not forced.
            excluded += 1
        else:
            nums.append(parsed)
    if not nums:
        return None
    floats = [float(n) for n in nums]
    mean = sum(nums) / Decimal(len(nums))
    std = Decimal(str(statistics.pstdev(floats))) if len(floats) > 1 else Decimal("0")
    sorted_nums = sorted(nums)
    mid = len(sorted_nums) // 2
    if len(sorted_nums) % 2:
        median = sorted_nums[mid]
    else:
        median = (sorted_nums[mid - 1] + sorted_nums[mid]) / Decimal(2)
    return NumericStatistics(
        minimum=min(nums),
        maximum=max(nums),
        mean=mean,
        median=median,
        standard_deviation=std,
        zero_count=sum(1 for n in nums if n == 0),
        negative_count=sum(1 for n in nums if n < 0),
        positive_count=sum(1 for n in nums if n > 0),
        excluded_incompatible_count=excluded,
    )


def _temporal_stats(values: list[NormalizedValue]) -> TemporalStatistics | None:
    parsed_rows: list[tuple[NormalizedValue, datetime]] = []
    patterns: Counter[str] = Counter()
    ambiguous_count = 0

    for item in values:
        if not item.has_content and item.kind not in {
            CellValueKind.DATE,
            CellValueKind.DATETIME,
            CellValueKind.TIME,
        }:
            continue
        result = parse_temporal_value(kind=item.kind, original=item.original or item.trimmed)
        if result is None:
            continue
        if result.ambiguous:
            ambiguous_count += 1
            if result.pattern:
                patterns[result.pattern] += 1
            continue
        if result.sort_key is None:
            continue
        parsed_rows.append((item, result.sort_key))
        patterns[result.pattern or item.kind.value] += 1

    if not parsed_rows:
        return None

    ordered = sorted(parsed_rows, key=lambda pair: pair[1])
    min_item, min_key = ordered[0]
    max_item, max_key = ordered[-1]

    chrono = None
    if len(parsed_rows) > 1:
        pairs = sum(
            1 for i in range(1, len(parsed_rows)) if parsed_rows[i][1] >= parsed_rows[i - 1][1]
        )
        chrono = pairs / (len(parsed_rows) - 1)

    dominant = patterns.most_common(1)[0][0] if patterns else None
    min_original = min_item.original or min_item.trimmed or str(min_key)
    max_original = max_item.original or max_item.trimmed or str(max_key)
    return TemporalStatistics(
        minimum=min_original,
        maximum=max_original,
        range_label=f"{min_original}..{max_original}",
        distinct_count=len({key for _, key in parsed_rows}),
        chronological_order_ratio=chrono,
        dominant_pattern=dominant
        if ambiguous_count == 0
        else (f"{dominant}|ambiguous" if dominant else "ambiguous"),
    )


def build_column_statistics(
    data_values: list[NormalizedValue],
    *,
    options: ProfilingOptions,
    observed_count: int,
    unobserved_count: int,
) -> tuple[ColumnStatistics, Counter[str]]:
    total = len(data_values)
    content = sum(1 for item in data_values if item.has_content or item.is_formula)
    nulls = sum(1 for item in data_values if item.is_null and not item.is_formula)
    blanks = sum(1 for item in data_values if item.is_blank_string)
    whitespace = sum(1 for item in data_values if item.is_whitespace_only)
    formulas = sum(1 for item in data_values if item.is_formula)
    errors = sum(1 for item in data_values if item.is_error)

    counter: Counter[str] = Counter()
    truncated = False
    profiled = 0
    for item in data_values:
        profiled += 1
        if profiled > options.max_values_profiled_per_column:
            truncated = True
            break
        if item.is_formula or item.is_error:
            continue
        if item.is_null or item.is_blank_string or item.is_whitespace_only:
            continue
        key = item.trimmed if options.trim_strings_for_analysis else item.original
        if key is None:
            continue
        if not options.case_sensitive_cardinality and item.kind is CellValueKind.STRING:
            key = key.casefold()
        if len(counter) >= options.max_distinct_values_tracked and key not in counter:
            truncated = True
            continue
        counter[key] += 1

    distinct = len(counter)
    content_for_ratio = max(sum(counter.values()), 1)
    unique = sum(1 for count in counter.values() if count == 1)
    duplicates = sum(count - 1 for count in counter.values() if count > 1)
    exactness = StatisticExactness.TRUNCATED if truncated else StatisticExactness.EXACT

    # distinct_ratio: cardinality vs observed content.
    # unique_ratio: share of content values that appear exactly once (singletons / content).
    # Previously unique/distinct inflated uniqueness for sparse duplicate keys.
    stats = ColumnStatistics(
        total_row_count=total,
        observed_count=observed_count,
        content_count=content,
        null_count=nulls,
        blank_string_count=blanks,
        whitespace_only_count=whitespace,
        unobserved_count=unobserved_count,
        formula_count=formulas,
        error_count=errors,
        distinct_count=distinct,
        distinct_ratio=distinct / content_for_ratio,
        duplicate_count=duplicates,
        unique_count=unique,
        unique_ratio=unique / content_for_ratio,
        exactness=exactness,
        text=_text_stats(data_values),
        numeric=_numeric_stats(data_values),
        temporal=_temporal_stats(data_values),
    )
    return stats, counter
