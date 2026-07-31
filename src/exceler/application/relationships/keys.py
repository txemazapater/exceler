"""Primary and composite key discovery (Phase 2D)."""

from __future__ import annotations

from collections import Counter

from exceler.application.relationships.evidence import clamp, confidence_from_evidence
from exceler.application.relationships.value_index import ColumnValueSet
from exceler.domain.profiling.enums import LogicalValueType
from exceler.domain.relationships.enums import Exactness, KeyKind
from exceler.domain.relationships.models import (
    CompositeKeyCandidate,
    PrimaryKeyCandidate,
    RelationshipEvidenceItem,
    RelationshipStatistics,
)
from exceler.domain.relationships.options import RelationshipOptions

_PREFERRED_TYPES = {
    LogicalValueType.IDENTIFIER,
    LogicalValueType.UUID,
    LogicalValueType.CODE,
    LogicalValueType.INTEGER,
}
_PENALIZED_TYPES = {
    LogicalValueType.BOOLEAN,
    LogicalValueType.CURRENCY,
    LogicalValueType.PERCENTAGE,
    LogicalValueType.TEXT,
    LogicalValueType.EMPTY,
    LogicalValueType.UNKNOWN,
}


def discover_primary_keys(
    columns: list[ColumnValueSet],
    *,
    options: RelationshipOptions,
) -> list[PrimaryKeyCandidate]:
    by_region: dict[str, list[ColumnValueSet]] = {}
    for col in columns:
        by_region.setdefault(col.ref.region_id, []).append(col)

    results: list[PrimaryKeyCandidate] = []
    for _region_id, cols in sorted(by_region.items()):
        ranked = sorted(
            (_score_pk(col, options) for col in cols),
            key=lambda item: (-item.confidence, item.column.column_index, item.column.column_id),
        )
        results.extend(ranked[: options.max_pk_candidates_per_region])
    return results


def _score_pk(col: ColumnValueSet, options: RelationshipOptions) -> PrimaryKeyCandidate:
    total = max(len(col.row_values), 1)
    distinct_ratio = len(col.distinct) / max(col.content_count, 1) if col.content_count else 0.0
    null_ratio = col.nullish_count / total
    non_null_ratio = 1.0 - null_ratio
    logical = col.profile.logical_type_inference.selected_type
    identifier = col.profile.identifier_analysis

    evidence: list[RelationshipEvidenceItem] = []
    warnings = list(col.warnings)

    evidence.append(
        RelationshipEvidenceItem(
            "distinct_ratio",
            options.weight_distinct * distinct_ratio,
            f"distinct_ratio={distinct_ratio:.4f}",
            {"distinct_ratio": distinct_ratio},
        )
    )
    evidence.append(
        RelationshipEvidenceItem(
            "non_null_ratio",
            options.weight_non_null * non_null_ratio,
            f"non_null_ratio={non_null_ratio:.4f}",
            {"non_null_ratio": non_null_ratio},
        )
    )
    if identifier.is_candidate:
        evidence.append(
            RelationshipEvidenceItem(
                "identifier_candidate",
                options.weight_identifier * identifier.confidence,
                "profiling identifier candidate",
            )
        )
    if logical in _PREFERRED_TYPES:
        evidence.append(
            RelationshipEvidenceItem(
                "logical_type_preferred",
                options.weight_logical_type,
                f"logical_type={logical.value}",
            )
        )
    elif logical in _PENALIZED_TYPES:
        evidence.append(
            RelationshipEvidenceItem(
                "logical_type_penalized",
                -options.weight_logical_type,
                f"logical_type={logical.value} unlikely for key",
            )
        )
        warnings.append(f"Logical type {logical.value} is unlikely for a primary key.")

    if distinct_ratio < options.min_pk_distinct_ratio:
        evidence.append(
            RelationshipEvidenceItem(
                "below_distinct_threshold",
                -0.25,
                "distinct_ratio below primary-key threshold",
            )
        )
    if non_null_ratio < options.min_pk_non_null_ratio:
        evidence.append(
            RelationshipEvidenceItem(
                "below_non_null_threshold",
                -0.2,
                "null ratio above primary-key threshold",
            )
        )

    penalty = options.truncation_penalty if col.exactness is Exactness.TRUNCATED else 0.0
    confidence = confidence_from_evidence(evidence, penalty=penalty)

    key_kind = KeyKind.PRIMARY
    if logical is LogicalValueType.INTEGER and distinct_ratio >= options.min_pk_distinct_ratio:
        key_kind = KeyKind.SURROGATE
    elif logical in {LogicalValueType.CODE, LogicalValueType.IDENTIFIER, LogicalValueType.UUID}:
        key_kind = KeyKind.NATURAL

    return PrimaryKeyCandidate(
        column=col.ref,
        confidence=confidence,
        key_kind=key_kind,
        statistics=RelationshipStatistics(
            distinct_count=len(col.distinct),
            distinct_ratio=distinct_ratio,
            null_ratio=null_ratio,
            content_count=col.content_count,
            exactness=col.exactness,
        ),
        evidence=tuple(evidence),
        warnings=tuple(warnings),
    )


def discover_composite_keys(
    columns: list[ColumnValueSet],
    *,
    options: RelationshipOptions,
) -> list[CompositeKeyCandidate]:
    by_region: dict[str, list[ColumnValueSet]] = {}
    for col in columns:
        by_region.setdefault(col.ref.region_id, []).append(col)

    results: list[CompositeKeyCandidate] = []
    for _region_id, cols in sorted(by_region.items()):
        # Candidates: not unique alone, but have moderate distinctness.
        weak = [
            col
            for col in cols
            if col.content_count >= 2
            and (
                0.2
                <= (len(col.distinct) / max(col.content_count, 1))
                < options.min_pk_distinct_ratio
            )
        ]
        weak.sort(
            key=lambda col: (
                -(len(col.distinct) / max(col.content_count, 1)),
                col.ref.column_index,
            )
        )
        weak = weak[: options.max_composite_pair_columns]
        for i, left in enumerate(weak):
            for right in weak[i + 1 :]:
                candidate = _score_pair(left, right, options)
                if candidate is not None:
                    results.append(candidate)
    results.sort(
        key=lambda item: (
            -item.confidence,
            item.columns[0].column_id,
            item.columns[1].column_id,
        )
    )
    return results


def _score_pair(
    left: ColumnValueSet,
    right: ColumnValueSet,
    options: RelationshipOptions,
) -> CompositeKeyCandidate | None:
    if len(left.row_values) != len(right.row_values):
        return None
    pairs: list[tuple[str, str]] = []
    truncated = left.exactness is Exactness.TRUNCATED or right.exactness is Exactness.TRUNCATED
    for a, b in zip(left.row_values, right.row_values, strict=True):
        if a is None or b is None:
            continue
        pairs.append((a, b))
    if len(pairs) < 2:
        return None
    counter = Counter(pairs)
    if len(counter) > options.max_distinct_values_tracked:
        truncated = True
        # Keep deterministic subset for ratio estimate
        keys = sorted(counter.keys())[: options.max_distinct_values_tracked]
        counter = Counter({key: counter[key] for key in keys})
    distinct_ratio = len(counter) / max(len(pairs), 1)
    if distinct_ratio < options.min_pk_distinct_ratio:
        return None
    # Require both sides alone not unique
    left_ratio = len(left.distinct) / max(left.content_count, 1)
    right_ratio = len(right.distinct) / max(right.content_count, 1)
    if left_ratio >= options.min_pk_distinct_ratio or right_ratio >= options.min_pk_distinct_ratio:
        return None

    evidence = [
        RelationshipEvidenceItem(
            "joint_unique",
            0.55,
            f"joint_distinct_ratio={distinct_ratio:.4f}",
            {"joint_distinct_ratio": distinct_ratio},
        ),
        RelationshipEvidenceItem(
            "parts_not_unique",
            0.35,
            f"left_ratio={left_ratio:.4f} right_ratio={right_ratio:.4f}",
        ),
    ]
    penalty = options.truncation_penalty if truncated else 0.0
    confidence = confidence_from_evidence(evidence, penalty=penalty)
    cols = tuple(sorted([left.ref, right.ref], key=lambda ref: (ref.column_index, ref.column_id)))
    return CompositeKeyCandidate(
        columns=cols,
        confidence=clamp(confidence),
        joint_distinct_ratio=distinct_ratio,
        joint_content_count=len(pairs),
        exactness=Exactness.TRUNCATED if truncated else Exactness.EXACT,
        evidence=tuple(evidence),
        warnings=tuple(dict.fromkeys([*left.warnings, *right.warnings])),
    )
