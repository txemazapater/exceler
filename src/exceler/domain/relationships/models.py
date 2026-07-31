"""Relationship and key candidate domain models (Phase 2D)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from exceler.domain.relationships.enums import (
    Exactness,
    GraphEdgeKind,
    GraphNodeKind,
    KeyKind,
    RelationshipCardinality,
)


@dataclass(frozen=True)
class RelationshipEvidenceItem:
    code: str
    weight: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "weight": self.weight,
            "message": self.message,
        }
        if self.details:
            payload["details"] = dict(self.details)
        return payload


@dataclass(frozen=True)
class ColumnRef:
    column_id: str
    sheet_name: str
    region_id: str
    column_index: int
    column_letter: str
    effective_name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "column_id": self.column_id,
            "sheet_name": self.sheet_name,
            "region_id": self.region_id,
            "column_index": self.column_index,
            "column_letter": self.column_letter,
            "effective_name": self.effective_name,
        }


@dataclass(frozen=True)
class RelationshipStatistics:
    distinct_count: int
    distinct_ratio: float
    null_ratio: float
    content_count: int
    exactness: Exactness

    def to_dict(self) -> dict[str, Any]:
        return {
            "distinct_count": self.distinct_count,
            "distinct_ratio": self.distinct_ratio,
            "null_ratio": self.null_ratio,
            "content_count": self.content_count,
            "exactness": self.exactness.value,
        }


@dataclass(frozen=True)
class PrimaryKeyCandidate:
    column: ColumnRef
    confidence: float
    key_kind: KeyKind
    statistics: RelationshipStatistics
    evidence: tuple[RelationshipEvidenceItem, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column.to_dict(),
            "confidence": self.confidence,
            "key_kind": self.key_kind.value,
            "statistics": self.statistics.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class CompositeKeyCandidate:
    columns: tuple[ColumnRef, ...]
    confidence: float
    joint_distinct_ratio: float
    joint_content_count: int
    exactness: Exactness
    evidence: tuple[RelationshipEvidenceItem, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "columns": [col.to_dict() for col in self.columns],
            "confidence": self.confidence,
            "joint_distinct_ratio": self.joint_distinct_ratio,
            "joint_content_count": self.joint_content_count,
            "exactness": self.exactness.value,
            "evidence": [item.to_dict() for item in self.evidence],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ForeignKeyCandidate:
    from_column: ColumnRef
    to_column: ColumnRef
    confidence: float
    inclusion_ratio: float
    coverage_ratio: float
    orphan_ratio: float
    orphan_count: int
    orphan_sample: tuple[str, ...]
    cardinality: RelationshipCardinality
    exactness: Exactness
    evidence: tuple[RelationshipEvidenceItem, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_column": self.from_column.to_dict(),
            "to_column": self.to_column.to_dict(),
            "confidence": self.confidence,
            "inclusion_ratio": self.inclusion_ratio,
            "coverage_ratio": self.coverage_ratio,
            "orphan_ratio": self.orphan_ratio,
            "orphan_count": self.orphan_count,
            "orphan_sample": list(self.orphan_sample),
            "cardinality": self.cardinality.value,
            "exactness": self.exactness.value,
            "evidence": [item.to_dict() for item in self.evidence],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class RelationshipCandidate:
    from_column: ColumnRef
    to_column: ColumnRef
    cardinality: RelationshipCardinality
    confidence: float
    foreign_key: ForeignKeyCandidate | None
    evidence: tuple[RelationshipEvidenceItem, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_column": self.from_column.to_dict(),
            "to_column": self.to_column.to_dict(),
            "cardinality": self.cardinality.value,
            "confidence": self.confidence,
            "foreign_key": self.foreign_key.to_dict() if self.foreign_key else None,
            "evidence": [item.to_dict() for item in self.evidence],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: GraphNodeKind
    label: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind.value,
            "label": self.label,
        }
        if self.details:
            payload["details"] = dict(self.details)
        return payload


@dataclass(frozen=True)
class GraphEdge:
    id: str
    kind: GraphEdgeKind
    source_id: str
    target_id: str
    confidence: float
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind.value,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "confidence": self.confidence,
        }
        if self.details:
            payload["details"] = dict(self.details)
        return payload


@dataclass(frozen=True)
class StructuralGraph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }


@dataclass(frozen=True)
class SheetRelationshipAnalysis:
    sheet_name: str
    sheet_index: int
    primary_keys: tuple[PrimaryKeyCandidate, ...]
    composite_keys: tuple[CompositeKeyCandidate, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sheet_name": self.sheet_name,
            "sheet_index": self.sheet_index,
            "primary_keys": [item.to_dict() for item in self.primary_keys],
            "composite_keys": [item.to_dict() for item in self.composite_keys],
        }


@dataclass(frozen=True)
class RelationshipAnalysisResult:
    workbook_hash: str
    inspector_version: str
    region_detector_version: str
    regions_schema_version: int
    profiler_version: str
    profiling_schema_version: int
    relationship_engine_version: str
    relationship_schema_version: int
    sheets: tuple[SheetRelationshipAnalysis, ...]
    foreign_keys: tuple[ForeignKeyCandidate, ...]
    relationships: tuple[RelationshipCandidate, ...]
    graph: StructuralGraph
    warnings: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "workbook_hash": self.workbook_hash,
            "inspector_version": self.inspector_version,
            "region_detector_version": self.region_detector_version,
            "regions_schema_version": self.regions_schema_version,
            "profiler_version": self.profiler_version,
            "profiling_schema_version": self.profiling_schema_version,
            "relationship_engine_version": self.relationship_engine_version,
            "relationship_schema_version": self.relationship_schema_version,
            "sheets": [sheet.to_dict() for sheet in self.sheets],
            "foreign_keys": [item.to_dict() for item in self.foreign_keys],
            "relationships": [item.to_dict() for item in self.relationships],
            "graph": self.graph.to_dict(),
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }
