"""Primary and composite key discovery (Phase 2D)."""

from __future__ import annotations

from collections import Counter

from exceler.application.relationships.evidence import confidence_from_evidence
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

# INTEGER is intentionally not preferred: uniqueness alone must not imply a surrogate key.
_PREFERRED_TYPES = {
    LogicalValueType.IDENTIFIER,
    LogicalValueType.UUID,
    LogicalValueType.CODE,
}
_PENALIZED_TYPES = {
    LogicalValueType.BOOLEAN,
    LogicalValueType.CURRENCY,
    LogicalValueType.PERCENTAGE,
    LogicalValueType.TEXT,
    LogicalValueType.EMPTY,
    LogicalValueType.UNKNOWN,
}
_NUMERIC_TYPES = {
    LogicalValueType.INTEGER,
    LogicalValueType.NUMBER,
    LogicalValueType.DECIMAL,
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
        scored = [_score_pk(col, options) for col in cols]
        accepted = [item for item in scored if item.accepted]
        rejected = [item for item in scored if not item.accepted]
        accepted.sort(
            key=lambda item: (-item.score, item.column.column_index, item.column.column_id)
        )
        rejected.sort(
            key=lambda item: (-item.score, item.column.column_index, item.column.column_id)
        )
        region_results = accepted[: options.max_pk_candidates_per_region]
        if options.emit_rejected_key_candidates:
            # Keep rejected visible (capped) so false positives remain inspectable.
            remaining = max(0, options.max_pk_candidates_per_region - len(region_results))
            region_results.extend(rejected[: max(remaining, 3)])
        results.extend(region_results)
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
    rejection_reasons: list[str] = []

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
        rejection_reasons.append("penalized_logical_type")

    if distinct_ratio < options.min_pk_distinct_ratio:
        rejection_reasons.append("below_min_pk_distinct_ratio")
        evidence.append(
            RelationshipEvidenceItem(
                "below_distinct_threshold",
                -0.25,
                "distinct_ratio below primary-key threshold",
            )
        )
    if non_null_ratio < options.min_pk_non_null_ratio:
        rejection_reasons.append("below_min_pk_non_null_ratio")
        evidence.append(
            RelationshipEvidenceItem(
                "below_non_null_threshold",
                -0.2,
                "null ratio above primary-key threshold",
            )
        )
    if col.content_count < 1:
        rejection_reasons.append("no_content_values")
    # Unique numerics are scored but not accepted as PK in 2D.2 (no SURROGATE shortcut).
    if logical in _NUMERIC_TYPES:
        rejection_reasons.append("numeric_logical_type_not_accepted")
        evidence.append(
            RelationshipEvidenceItem(
                "numeric_not_accepted_as_pk",
                -0.15,
                "numeric uniqueness alone is not accepted as primary key",
            )
        )

    penalty = options.truncation_penalty if col.exactness is Exactness.TRUNCATED else 0.0
    score = confidence_from_evidence(
        evidence,
        max_positive_weight=options.max_pk_positive_weight,
        penalty=penalty,
    )
    if score < options.min_pk_score:
        rejection_reasons.append("below_min_pk_score")

    accepted = not rejection_reasons
    # confidence mirrors score for ranking; acceptance is orthogonal.
    confidence = score

    # INTEGER + unique alone is never treated as SURROGATE (reserved for stronger evidence).
    key_kind = KeyKind.PRIMARY
    if logical in {LogicalValueType.CODE, LogicalValueType.IDENTIFIER, LogicalValueType.UUID}:
        key_kind = KeyKind.NATURAL

    return PrimaryKeyCandidate(
        column=col.ref,
        score=score,
        confidence=confidence,
        accepted=accepted,
        key_kind=key_kind,
        statistics=RelationshipStatistics(
            distinct_count=len(col.distinct),
            distinct_ratio=distinct_ratio,
            null_ratio=null_ratio,
            content_count=col.content_count,
            exactness=col.exactness,
        ),
        evidence=tuple(evidence),
        rejection_reasons=tuple(rejection_reasons),
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
                if candidate is not None and (
                    candidate.accepted or options.emit_rejected_key_candidates
                ):
                    results.append(candidate)
    results.sort(
        key=lambda item: (
            -int(item.accepted),
            -item.score,
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
        keys = sorted(counter.keys())[: options.max_distinct_values_tracked]
        counter = Counter({key: counter[key] for key in keys})
    distinct_ratio = len(counter) / max(len(pairs), 1)
    left_ratio = len(left.distinct) / max(left.content_count, 1)
    right_ratio = len(right.distinct) / max(right.content_count, 1)

    rejection_reasons: list[str] = []
    if distinct_ratio < options.min_pk_distinct_ratio:
        rejection_reasons.append("below_min_joint_distinct_ratio")
    if left_ratio >= options.min_pk_distinct_ratio or right_ratio >= options.min_pk_distinct_ratio:
        rejection_reasons.append("part_already_unique")

    evidence = [
        RelationshipEvidenceItem(
            "joint_unique",
            options.weight_joint_unique * distinct_ratio,
            f"joint_distinct_ratio={distinct_ratio:.4f}",
            {"joint_distinct_ratio": distinct_ratio},
        ),
        RelationshipEvidenceItem(
            "parts_not_unique",
            options.weight_parts_not_unique
            * (1.0 if left_ratio < options.min_pk_distinct_ratio else 0.0)
            * (1.0 if right_ratio < options.min_pk_distinct_ratio else 0.0),
            f"left_ratio={left_ratio:.4f} right_ratio={right_ratio:.4f}",
        ),
    ]
    penalty = options.truncation_penalty if truncated else 0.0
    score = confidence_from_evidence(
        evidence,
        max_positive_weight=options.max_composite_positive_weight,
        penalty=penalty,
    )
    if score < options.min_pk_score:
        rejection_reasons.append("below_min_pk_score")

    # Drop pairs that never approached composite uniqueness unless emitting rejects.
    if "below_min_joint_distinct_ratio" in rejection_reasons and distinct_ratio < 0.5:
        return None

    accepted = not rejection_reasons
    cols = tuple(sorted([left.ref, right.ref], key=lambda ref: (ref.column_index, ref.column_id)))
    return CompositeKeyCandidate(
        columns=cols,
        score=score,
        confidence=score,
        accepted=accepted,
        joint_distinct_ratio=distinct_ratio,
        joint_content_count=len(pairs),
        exactness=Exactness.TRUNCATED if truncated else Exactness.EXACT,
        evidence=tuple(evidence),
        rejection_reasons=tuple(rejection_reasons),
        warnings=tuple(dict.fromkeys([*left.warnings, *right.warnings])),
    )
