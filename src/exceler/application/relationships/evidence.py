"""Evidence aggregation helpers for Phase 2D."""

from __future__ import annotations

from exceler.domain.relationships.models import RelationshipEvidenceItem


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def confidence_from_evidence(
    items: list[RelationshipEvidenceItem],
    *,
    penalty: float = 0.0,
) -> float:
    if not items:
        return clamp(0.0 - penalty)
    total_weight = sum(max(item.weight, 0.0) for item in items)
    if total_weight <= 0:
        return clamp(0.0 - penalty)
    # Positive evidence codes contribute; negative weights pull down.
    score = sum(item.weight for item in items) / max(abs(total_weight), 1e-9)
    # Normalize: treat sum of positive weights as denominator when mixed.
    positive = sum(item.weight for item in items if item.weight > 0)
    if positive > 0:
        score = sum(item.weight for item in items if item.weight > 0) / positive
        neg = sum(-item.weight for item in items if item.weight < 0)
        score = score * (1.0 - min(1.0, neg / (positive + neg + 1e-9)))
    return clamp(score - penalty)
