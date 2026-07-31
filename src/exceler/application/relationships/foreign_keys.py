"""Foreign key and relationship discovery (Phase 2D)."""

from __future__ import annotations

from collections import Counter

from exceler.application.relationships.domain_compat import (
    domain_compatibility_score,
    logical_types_compatible,
)
from exceler.application.relationships.evidence import confidence_from_evidence
from exceler.application.relationships.identifier_signals import (
    SemanticCompatibilityStatus,
    extract_identifier_semantic_signal,
    has_child_reference_evidence,
    has_independent_identifier_evidence,
    reference_target_semantically_compatible,
)
from exceler.application.relationships.value_index import ColumnValueSet
from exceler.domain.relationships.enums import Exactness, RelationshipCardinality
from exceler.domain.relationships.models import (
    ForeignKeyCandidate,
    RelationshipCandidate,
    RelationshipEvidenceItem,
)
from exceler.domain.relationships.options import RelationshipOptions


def discover_foreign_keys(
    columns: list[ColumnValueSet],
    *,
    options: RelationshipOptions,
) -> list[ForeignKeyCandidate]:
    candidates: list[ForeignKeyCandidate] = []
    comparisons = 0
    # Prefer parent-like columns (high uniqueness) as targets.
    parents = sorted(
        columns,
        key=lambda col: (
            -(len(col.distinct) / max(col.content_count, 1)),
            col.ref.sheet_name,
            col.ref.region_id,
            col.ref.column_index,
        ),
    )
    children = sorted(
        columns,
        key=lambda col: (col.ref.sheet_name, col.ref.region_id, col.ref.column_index),
    )

    for child in children:
        if child.content_count < 1 or not child.distinct:
            continue
        child_type = child.profile.logical_type_inference.selected_type
        child_ratio = len(child.distinct) / max(child.content_count, 1)
        for parent in parents:
            if comparisons >= options.max_fk_pair_comparisons:
                break
            if child.ref.column_id == parent.ref.column_id:
                continue
            if child.ref.region_id == parent.ref.region_id:
                continue
            if not parent.distinct:
                continue
            parent_type = parent.profile.logical_type_inference.selected_type
            if not logical_types_compatible(child_type, parent_type):
                continue
            domain_score = domain_compatibility_score(child, parent)
            if domain_score < options.min_domain_compat_score:
                continue
            comparisons += 1
            parent_ratio = len(parent.distinct) / max(parent.content_count, 1)
            # Parent side should look key-like for directed FK candidates.
            if parent_ratio < options.min_fk_parent_distinct_ratio:
                continue
            # Unique smaller set ⊆ larger set is almost always reversed direction
            # (true orphans make the child domain larger than the parent key).
            if (
                child.distinct <= parent.distinct
                and len(parent.distinct) > len(child.distinct)
                and child_ratio >= 0.98
            ):
                continue
            candidate = _score_fk(child, parent, domain_score, options)
            if candidate is None:
                continue
            # Prefer child less unique than parent for classic FK direction.
            if child_ratio > parent_ratio + 0.05 and candidate.inclusion_ratio < 0.99:
                continue
            candidates.append(candidate)
        if comparisons >= options.max_fk_pair_comparisons:
            break

    candidates.sort(
        key=lambda item: (
            -int(item.accepted),
            -item.score,
            -item.inclusion_ratio,
            item.from_column.column_id,
            item.to_column.column_id,
        )
    )
    return candidates[: options.max_fk_candidates]


def _score_fk(
    child: ColumnValueSet,
    parent: ColumnValueSet,
    domain_score: float,
    options: RelationshipOptions,
) -> ForeignKeyCandidate | None:
    child_values = {v for v in child.distinct}
    parent_values = parent.distinct
    if not child_values:
        return None

    orphans = sorted(child_values - parent_values)
    included = len(child_values) - len(orphans)
    inclusion = included / max(len(child_values), 1)
    if inclusion < options.min_fk_inclusion_ratio:
        return None

    # Coverage: how much of the parent domain is referenced.
    coverage = len(child_values & parent_values) / max(len(parent_values), 1)
    orphan_ratio = len(orphans) / max(len(child_values), 1)
    parent_unique = len(parent.distinct) / max(parent.content_count, 1)
    child_unique = len(child.distinct) / max(child.content_count, 1)

    cardinality = _infer_cardinality(child, parent)
    truncated = child.exactness is Exactness.TRUNCATED or parent.exactness is Exactness.TRUNCATED
    parent_independent = has_independent_identifier_evidence(parent)
    child_reference = has_child_reference_evidence(child)
    child_independent = has_independent_identifier_evidence(child)
    reverse_inclusion = (
        len(parent_values & child_values) / max(len(parent_values), 1) if parent_values else 0.0
    )

    evidence = [
        RelationshipEvidenceItem(
            "inclusion_ratio",
            options.weight_inclusion * inclusion,
            f"inclusion_ratio={inclusion:.4f}",
            {"inclusion_ratio": inclusion},
        ),
        RelationshipEvidenceItem(
            "parent_uniqueness",
            options.weight_parent_unique * parent_unique,
            f"parent_distinct_ratio={parent_unique:.4f}",
        ),
        RelationshipEvidenceItem(
            "domain_compatibility",
            options.weight_domain_compat * domain_score,
            f"domain_compat={domain_score:.4f}",
        ),
        RelationshipEvidenceItem(
            "logical_type_compatible",
            options.weight_type_compat,
            "logical types compatible",
        ),
    ]
    rejection_reasons: list[str] = []
    if orphan_ratio > 0:
        evidence.append(
            RelationshipEvidenceItem(
                "orphans_present",
                -options.orphan_penalty_factor * orphan_ratio,
                f"orphan_ratio={orphan_ratio:.4f} orphan_count={len(orphans)}",
            )
        )

    # 2D.4: destination must be an independently evidenced identifier.
    if not parent_independent:
        rejection_reasons.append("insufficient_independent_identifier_evidence")
        evidence.append(
            RelationshipEvidenceItem(
                "insufficient_independent_identifier_evidence",
                -0.2,
                "destination lacks independent identifier evidence",
                {
                    "has_independent_identifier_evidence": False,
                    "has_relationship_support": False,
                },
            )
        )
    else:
        evidence.append(
            RelationshipEvidenceItem(
                "parent_independent_identifier",
                0.1,
                "destination has independent identifier evidence",
                {"has_independent_identifier_evidence": True},
            )
        )

    # 2D.5: child must look like a reference (header/type), not a measure.
    if not child_reference:
        rejection_reasons.append("insufficient_child_reference_evidence")
        evidence.append(
            RelationshipEvidenceItem(
                "insufficient_child_reference_evidence",
                -0.2,
                "source lacks child reference evidence",
                {"has_child_reference_evidence": False},
            )
        )
    else:
        evidence.append(
            RelationshipEvidenceItem(
                "child_reference_evidence",
                0.05,
                "source has child reference evidence",
                {"has_child_reference_evidence": True},
            )
        )

    # 2D.6: reference/target headers must describe a compatible entity.
    child_signal = extract_identifier_semantic_signal(child.ref.effective_name)
    parent_signal = extract_identifier_semantic_signal(parent.ref.effective_name)
    semantic = reference_target_semantically_compatible(child_signal, parent_signal)
    semantic_payload = {
        "status": semantic.status.value,
        "child_canonical_entity": child_signal.canonical_entity,
        "parent_canonical_entity": parent_signal.canonical_entity,
        "child_entity_tokens": list(child_signal.entity_tokens),
        "parent_entity_tokens": list(parent_signal.entity_tokens),
        "child_structural_tokens": list(child_signal.structural_tokens),
        "parent_structural_tokens": list(parent_signal.structural_tokens),
        "shared_entities": list(semantic.shared_entities),
    }
    if semantic.status is SemanticCompatibilityStatus.COMPATIBLE:
        evidence.append(
            RelationshipEvidenceItem(
                "semantic_entity_compatibility",
                options.weight_semantic_entity,
                semantic.detail,
                semantic_payload,
            )
        )
    elif semantic.status is SemanticCompatibilityStatus.INCOMPATIBLE:
        rejection_reasons.append("incompatible_reference_target_semantics")
        evidence.append(
            RelationshipEvidenceItem(
                "semantic_entity_mismatch",
                -options.weight_semantic_entity,
                semantic.detail,
                semantic_payload,
            )
        )
    elif semantic.status is SemanticCompatibilityStatus.AMBIGUOUS:
        rejection_reasons.append("ambiguous_reference_target_semantics")
        evidence.append(
            RelationshipEvidenceItem(
                "ambiguous_reference_target_semantics",
                -0.15,
                semantic.detail,
                semantic_payload,
            )
        )
    else:
        if options.require_reference_target_semantics:
            rejection_reasons.append("insufficient_reference_target_semantics")
        evidence.append(
            RelationshipEvidenceItem(
                "insufficient_reference_target_semantics",
                -0.1,
                semantic.detail,
                semantic_payload,
            )
        )

    # Symmetric unique domains with mutual inclusion and no clear orientation.
    if (
        parent_unique >= 0.98
        and child_unique >= 0.98
        and inclusion >= 0.99
        and reverse_inclusion >= 0.99
    ):
        if not (parent_independent and not child_independent):
            rejection_reasons.append("ambiguous_relationship_direction")
            evidence.append(
                RelationshipEvidenceItem(
                    "ambiguous_relationship_direction",
                    -0.25,
                    "both sides unique with mutual inclusion; direction unresolved",
                    {
                        "child_unique": child_unique,
                        "parent_unique": parent_unique,
                        "reverse_inclusion": reverse_inclusion,
                    },
                )
            )

    penalty = options.truncation_penalty if truncated else 0.0
    # Parent/child identity bonuses are small additives outside the core FK weight budget.
    score = confidence_from_evidence(
        evidence,
        max_positive_weight=options.max_fk_positive_weight + 0.15,
        penalty=penalty,
    )
    if score < options.min_fk_score:
        rejection_reasons.append("below_min_fk_score")
    accepted = not rejection_reasons

    return ForeignKeyCandidate(
        from_column=child.ref,
        to_column=parent.ref,
        score=score,
        confidence=score,
        accepted=accepted,
        inclusion_ratio=inclusion,
        coverage_ratio=coverage,
        orphan_ratio=orphan_ratio,
        orphan_count=len(orphans),
        orphan_sample=tuple(orphans[: options.orphan_sample_limit]),
        cardinality=cardinality,
        exactness=Exactness.TRUNCATED if truncated else Exactness.EXACT,
        evidence=tuple(evidence),
        rejection_reasons=tuple(dict.fromkeys(rejection_reasons)),
        warnings=tuple(dict.fromkeys([*child.warnings, *parent.warnings])),
    )


def _infer_cardinality(
    child: ColumnValueSet,
    parent: ColumnValueSet,
) -> RelationshipCardinality:
    child_ratio = len(child.distinct) / max(child.content_count, 1)
    parent_ratio = len(parent.distinct) / max(parent.content_count, 1)
    # Multiplicity on child side: value frequency
    freqs = Counter(v for v in child.row_values if v is not None)
    max_freq = max(freqs.values()) if freqs else 1

    if parent_ratio >= 0.98 and child_ratio >= 0.98 and max_freq == 1:
        return RelationshipCardinality.ONE_TO_ONE
    if parent_ratio >= 0.95 and max_freq > 1:
        return RelationshipCardinality.ONE_TO_MANY
    # Mutual non-uniqueness + strong overlap suggests bridge / M:N
    overlap = len(child.distinct & parent.distinct) / max(len(child.distinct | parent.distinct), 1)
    if child_ratio < 0.95 and parent_ratio < 0.95 and overlap >= 0.5:
        return RelationshipCardinality.MANY_TO_MANY
    if parent_ratio >= 0.9:
        return RelationshipCardinality.ONE_TO_MANY
    return RelationshipCardinality.UNKNOWN


def relationships_from_foreign_keys(
    foreign_keys: list[ForeignKeyCandidate],
) -> list[RelationshipCandidate]:
    results: list[RelationshipCandidate] = []
    for fk in foreign_keys:
        if not fk.accepted:
            continue
        results.append(
            RelationshipCandidate(
                from_column=fk.from_column,
                to_column=fk.to_column,
                cardinality=fk.cardinality,
                confidence=fk.confidence,
                foreign_key=fk,
                evidence=fk.evidence,
                warnings=fk.warnings,
            )
        )
    return results
