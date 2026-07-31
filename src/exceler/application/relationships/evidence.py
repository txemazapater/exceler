"""Evidence aggregation helpers for Phase 2D."""

from __future__ import annotations

from exceler.domain.relationships.models import RelationshipEvidenceItem


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def confidence_from_evidence(
    items: list[RelationshipEvidenceItem],
    *,
    max_positive_weight: float,
    penalty: float = 0.0,
) -> float:
    """Calibrate score against the theoretical max positive weight, not present evidence.

    Positive item weights are contributions toward ``max_positive_weight``.
    Negative weights reduce the score proportionally to the same denominator.
    """
    if max_positive_weight <= 0:
        return clamp(0.0 - penalty)
    positive = sum(item.weight for item in items if item.weight > 0)
    negative = sum(-item.weight for item in items if item.weight < 0)
    score = positive / max_positive_weight
    score -= negative / max_positive_weight
    return clamp(score - penalty)
