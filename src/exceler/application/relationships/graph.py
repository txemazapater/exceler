"""Structural graph construction for Phase 2D."""

from __future__ import annotations

from exceler.application.relationships.value_index import ColumnValueSet
from exceler.domain.relationships.enums import GraphEdgeKind, GraphNodeKind
from exceler.domain.relationships.models import (
    CompositeKeyCandidate,
    ForeignKeyCandidate,
    GraphEdge,
    GraphNode,
    PrimaryKeyCandidate,
    StructuralGraph,
)
from exceler.domain.workbook.models import WorkbookInspection


def build_structural_graph(
    inspection: WorkbookInspection,
    columns: list[ColumnValueSet],
    primary_keys: list[PrimaryKeyCandidate],
    composite_keys: list[CompositeKeyCandidate],
    foreign_keys: list[ForeignKeyCandidate],
) -> StructuralGraph:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    wb_id = f"workbook::{inspection.file.content_hash[:12]}"
    nodes.append(
        GraphNode(
            id=wb_id,
            kind=GraphNodeKind.WORKBOOK,
            label=inspection.file.file_name,
            details={"content_hash": inspection.file.content_hash},
        )
    )

    sheet_ids: dict[str, str] = {}
    for ws in inspection.worksheets:
        sid = f"sheet::{ws.name}"
        sheet_ids[ws.name] = sid
        nodes.append(GraphNode(id=sid, kind=GraphNodeKind.WORKSHEET, label=ws.name))
        edges.append(
            GraphEdge(
                id=f"contains::{wb_id}::{sid}",
                kind=GraphEdgeKind.CONTAINS,
                source_id=wb_id,
                target_id=sid,
                confidence=1.0,
            )
        )

    region_ids: set[str] = set()
    for col in columns:
        rid = f"region::{col.ref.region_id}"
        if rid not in region_ids:
            region_ids.add(rid)
            nodes.append(
                GraphNode(
                    id=rid,
                    kind=GraphNodeKind.REGION,
                    label=col.ref.region_id,
                    details={"sheet_name": col.ref.sheet_name},
                )
            )
            parent_sheet_id = sheet_ids.get(col.ref.sheet_name)
            if parent_sheet_id:
                edges.append(
                    GraphEdge(
                        id=f"contains::{parent_sheet_id}::{rid}",
                        kind=GraphEdgeKind.CONTAINS,
                        source_id=parent_sheet_id,
                        target_id=rid,
                        confidence=1.0,
                    )
                )
        cid = f"column::{col.ref.column_id}"
        nodes.append(
            GraphNode(
                id=cid,
                kind=GraphNodeKind.COLUMN,
                label=col.ref.effective_name,
                details={
                    "column_index": col.ref.column_index,
                    "region_id": col.ref.region_id,
                    "sheet_name": col.ref.sheet_name,
                },
            )
        )
        edges.append(
            GraphEdge(
                id=f"contains::{rid}::{cid}",
                kind=GraphEdgeKind.CONTAINS,
                source_id=rid,
                target_id=cid,
                confidence=1.0,
            )
        )

    for pk in primary_keys:
        if not pk.accepted:
            continue
        edges.append(
            GraphEdge(
                id=f"pk::{pk.column.column_id}",
                kind=GraphEdgeKind.CANDIDATE_KEY,
                source_id=f"region::{pk.column.region_id}",
                target_id=f"column::{pk.column.column_id}",
                confidence=pk.confidence,
                details={"key_kind": pk.key_kind.value},
            )
        )
    for ck in composite_keys:
        if not ck.accepted:
            continue
        edge_id = "composite::" + "+".join(cref.column_id for cref in ck.columns)
        for cref in ck.columns:
            edges.append(
                GraphEdge(
                    id=f"{edge_id}::{cref.column_id}",
                    kind=GraphEdgeKind.CANDIDATE_KEY,
                    source_id=f"region::{cref.region_id}",
                    target_id=f"column::{cref.column_id}",
                    confidence=ck.confidence,
                    details={"composite": True},
                )
            )
    for fk in foreign_keys:
        if not fk.accepted:
            continue
        edges.append(
            GraphEdge(
                id=f"fk::{fk.from_column.column_id}::{fk.to_column.column_id}",
                kind=GraphEdgeKind.CANDIDATE_FOREIGN_KEY,
                source_id=f"column::{fk.from_column.column_id}",
                target_id=f"column::{fk.to_column.column_id}",
                confidence=fk.confidence,
                details={
                    "cardinality": fk.cardinality.value,
                    "inclusion_ratio": fk.inclusion_ratio,
                },
            )
        )
        edges.append(
            GraphEdge(
                id=f"rel::{fk.from_column.column_id}::{fk.to_column.column_id}",
                kind=GraphEdgeKind.CANDIDATE_RELATIONSHIP,
                source_id=f"column::{fk.from_column.column_id}",
                target_id=f"column::{fk.to_column.column_id}",
                confidence=fk.confidence,
                details={"cardinality": fk.cardinality.value},
            )
        )

    nodes.sort(key=lambda node: (node.kind.value, node.id))
    edges.sort(key=lambda edge: (edge.kind.value, edge.id))
    return StructuralGraph(nodes=tuple(nodes), edges=tuple(edges))
