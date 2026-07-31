"""Serialization for Phase 2D relationship analysis."""

from __future__ import annotations

from typing import Any

from exceler.domain.relationships.models import RelationshipAnalysisResult


def relationships_to_dict(result: RelationshipAnalysisResult) -> dict[str, Any]:
    return result.to_dict()
