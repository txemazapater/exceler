"""Domain compatibility between columns (structural, no names)."""

from __future__ import annotations

from collections import Counter

from exceler.application.profiling.normalization import abstract_pattern
from exceler.application.relationships.value_index import ColumnValueSet
from exceler.domain.profiling.enums import LogicalValueType

_COMPATIBLE_TYPES: dict[LogicalValueType, set[LogicalValueType]] = {
    LogicalValueType.INTEGER: {
        LogicalValueType.INTEGER,
        LogicalValueType.NUMBER,
        LogicalValueType.CODE,
        LogicalValueType.IDENTIFIER,
    },
    LogicalValueType.DECIMAL: {LogicalValueType.DECIMAL, LogicalValueType.NUMBER},
    LogicalValueType.NUMBER: {
        LogicalValueType.INTEGER,
        LogicalValueType.DECIMAL,
        LogicalValueType.NUMBER,
    },
    LogicalValueType.CODE: {
        LogicalValueType.CODE,
        LogicalValueType.IDENTIFIER,
        LogicalValueType.TEXT,
        LogicalValueType.INTEGER,
    },
    LogicalValueType.IDENTIFIER: {
        LogicalValueType.IDENTIFIER,
        LogicalValueType.CODE,
        LogicalValueType.UUID,
        LogicalValueType.TEXT,
        LogicalValueType.INTEGER,
    },
    LogicalValueType.UUID: {
        LogicalValueType.UUID,
        LogicalValueType.IDENTIFIER,
        LogicalValueType.CODE,
    },
    LogicalValueType.TEXT: {
        LogicalValueType.TEXT,
        LogicalValueType.CODE,
        LogicalValueType.IDENTIFIER,
    },
    LogicalValueType.DATE: {LogicalValueType.DATE, LogicalValueType.DATETIME},
    LogicalValueType.DATETIME: {LogicalValueType.DATETIME, LogicalValueType.DATE},
    LogicalValueType.EMAIL: {LogicalValueType.EMAIL, LogicalValueType.TEXT},
    LogicalValueType.URL: {LogicalValueType.URL, LogicalValueType.TEXT},
    LogicalValueType.PHONE: {LogicalValueType.PHONE, LogicalValueType.TEXT, LogicalValueType.CODE},
    LogicalValueType.POSTAL_CODE: {
        LogicalValueType.POSTAL_CODE,
        LogicalValueType.CODE,
        LogicalValueType.TEXT,
    },
}


def logical_types_compatible(a: LogicalValueType, b: LogicalValueType) -> bool:
    if a is b:
        return True
    return b in _COMPATIBLE_TYPES.get(a, set()) or a in _COMPATIBLE_TYPES.get(b, set())


def domain_compatibility_score(left: ColumnValueSet, right: ColumnValueSet) -> float:
    """Structural domain overlap in [0, 1] without using column names."""
    if not left.distinct or not right.distinct:
        return 0.0

    left_lens = [len(v) for v in left.distinct]
    right_lens = [len(v) for v in right.distinct]
    left_avg = sum(left_lens) / len(left_lens)
    right_avg = sum(right_lens) / len(right_lens)
    length_score = 1.0 - min(1.0, abs(left_avg - right_avg) / max(left_avg, right_avg, 1.0))

    left_patterns = Counter(abstract_pattern(v) for v in list(left.distinct)[:500])
    right_patterns = Counter(abstract_pattern(v) for v in list(right.distinct)[:500])
    shared = set(left_patterns) & set(right_patterns)
    if not left_patterns or not right_patterns:
        pattern_score = 0.0
    else:
        pattern_score = len(shared) / max(len(set(left_patterns) | set(right_patterns)), 1)

    # Cardinality similarity (log-ish via ratios)
    card_a = len(left.distinct) / max(left.content_count, 1)
    card_b = len(right.distinct) / max(right.content_count, 1)
    card_score = 1.0 - min(1.0, abs(card_a - card_b))

    overlap = len(left.distinct & right.distinct)
    union = len(left.distinct | right.distinct)
    jaccard = overlap / max(union, 1)

    return 0.25 * length_score + 0.30 * pattern_score + 0.15 * card_score + 0.30 * jaccard
