"""Domain exports for Phase 2D relationships."""

from exceler.domain.relationships.enums import (
    Exactness,
    GraphEdgeKind,
    GraphNodeKind,
    KeyKind,
    RelationshipCardinality,
)
from exceler.domain.relationships.errors import (
    InvalidRelationshipContractError,
    RelationshipError,
    RelationshipInputMismatchError,
    UnsupportedRelationshipInputVersionError,
)
from exceler.domain.relationships.models import (
    ColumnRef,
    CompositeKeyCandidate,
    ForeignKeyCandidate,
    GraphEdge,
    GraphNode,
    PrimaryKeyCandidate,
    RelationshipAnalysisResult,
    RelationshipCandidate,
    RelationshipEvidenceItem,
    RelationshipStatistics,
    SheetRelationshipAnalysis,
    StructuralGraph,
)
from exceler.domain.relationships.options import (
    RELATIONSHIP_ENGINE_VERSION,
    RELATIONSHIP_SCHEMA_VERSION,
    RelationshipOptions,
)

__all__ = [
    "RELATIONSHIP_ENGINE_VERSION",
    "RELATIONSHIP_SCHEMA_VERSION",
    "ColumnRef",
    "CompositeKeyCandidate",
    "Exactness",
    "ForeignKeyCandidate",
    "GraphEdge",
    "GraphEdgeKind",
    "GraphNode",
    "GraphNodeKind",
    "InvalidRelationshipContractError",
    "KeyKind",
    "PrimaryKeyCandidate",
    "RelationshipAnalysisResult",
    "RelationshipCandidate",
    "RelationshipCardinality",
    "RelationshipError",
    "RelationshipEvidenceItem",
    "RelationshipInputMismatchError",
    "RelationshipOptions",
    "RelationshipStatistics",
    "SheetRelationshipAnalysis",
    "StructuralGraph",
    "UnsupportedRelationshipInputVersionError",
]
