"""Deterministic relationship analyzer — inspection + regions + profiling only."""

from __future__ import annotations

from exceler.application.relationships.foreign_keys import (
    discover_foreign_keys,
    relationships_from_foreign_keys,
)
from exceler.application.relationships.graph import build_structural_graph
from exceler.application.relationships.keys import (
    discover_composite_keys,
    discover_primary_keys,
)
from exceler.application.relationships.value_index import build_column_value_sets
from exceler.domain.profiling.models import ProfilingResult
from exceler.domain.regions.models import RegionDetectionResult
from exceler.domain.relationships.errors import (
    InvalidRelationshipContractError,
    RelationshipInputMismatchError,
)
from exceler.domain.relationships.models import (
    RelationshipAnalysisResult,
    SheetRelationshipAnalysis,
)
from exceler.domain.relationships.options import (
    RELATIONSHIP_ENGINE_VERSION,
    RELATIONSHIP_SCHEMA_VERSION,
    RelationshipOptions,
)
from exceler.domain.workbook.enums import InspectionCompletionStatus
from exceler.domain.workbook.models import WorkbookInspection

_LIMITATIONS = (
    "Keys and relationships are structural candidates, not definitive constraints.",
    "Column names are never used as ranking signals among peers.",
    "Controlled header tokens may gate identity/reference evidence (token boundaries, 2D.5).",
    "FK acceptance requires reference-target semantic compatibility of header entities (2D.6).",
    "Formula cells contribute no key values (unevaluated).",
    "Analyzer consumes inspection + regions + profiling only; never re-reads Excel.",
    "Confidence is calibrated against max possible evidence weight (2D.2+).",
    "INTEGER uniqueness alone never implies SURROGATE key kind.",
    "Numeric PKs require independent identity evidence; FK support cannot create them (2D.4).",
    "FK sources require child reference evidence; value inclusion alone is insufficient (2D.5).",
    "Headers without entity tokens (Id/Code) do not invent relations from value overlap alone.",
    "Sheet/table names are not used to override incompatible column entities.",
    "Single-workbook analysis in 2D.6; multi-workbook support is reserved.",
)


def _validate_inputs(
    inspection: WorkbookInspection,
    regions: RegionDetectionResult,
    profiling: ProfilingResult,
) -> None:
    insp_hash = inspection.file.content_hash
    if insp_hash != regions.workbook_hash:
        raise RelationshipInputMismatchError(
            "WorkbookInspection.content_hash does not match RegionDetectionResult.workbook_hash."
        )
    if insp_hash != profiling.workbook_hash:
        raise RelationshipInputMismatchError(
            "WorkbookInspection.content_hash does not match ProfilingResult.workbook_hash."
        )
    if regions.workbook_hash != profiling.workbook_hash:
        raise RelationshipInputMismatchError(
            "RegionDetectionResult.workbook_hash does not match ProfilingResult.workbook_hash."
        )
    sheet_names = {ws.name for ws in inspection.worksheets}
    for region_sheet in regions.sheets:
        if region_sheet.sheet_name not in sheet_names:
            raise InvalidRelationshipContractError(
                f"Region sheet {region_sheet.sheet_name!r} missing from inspection."
            )
    for profile_sheet in profiling.sheets:
        if profile_sheet.sheet_name not in sheet_names:
            raise InvalidRelationshipContractError(
                f"Profiling sheet {profile_sheet.sheet_name!r} missing from inspection."
            )


class DeterministicRelationshipAnalyzer:
    def analyze(
        self,
        inspection: WorkbookInspection,
        regions: RegionDetectionResult,
        profiling: ProfilingResult,
        options: RelationshipOptions | None = None,
    ) -> RelationshipAnalysisResult:
        opts = options or RelationshipOptions()
        _validate_inputs(inspection, regions, profiling)

        warnings: list[str] = []
        if inspection.completion_status is InspectionCompletionStatus.PARTIAL:
            warnings.append("Underlying inspection was partial; key/FK metrics may be incomplete.")

        columns = build_column_value_sets(inspection, regions, profiling, opts)
        for col in columns:
            warnings.extend(col.warnings)

        # FK discovery first so relationship support can reinforce independently evidenced PKs.
        foreign_keys = discover_foreign_keys(columns, options=opts)
        referenced_column_ids = frozenset(
            fk.to_column.column_id for fk in foreign_keys if fk.accepted
        )
        primary_keys = discover_primary_keys(
            columns,
            options=opts,
            referenced_column_ids=referenced_column_ids,
        )
        composite_keys = discover_composite_keys(columns, options=opts)
        relationships = relationships_from_foreign_keys(foreign_keys)
        graph = build_structural_graph(
            inspection, columns, primary_keys, composite_keys, foreign_keys
        )

        # Group PK/composite by sheet
        sheet_index = {ws.name: idx for idx, ws in enumerate(inspection.worksheets)}
        sheet_names = sorted(
            {col.ref.sheet_name for col in columns},
            key=lambda n: sheet_index.get(n, 10_000),
        )
        sheets: list[SheetRelationshipAnalysis] = []
        for name in sheet_names:
            sheets.append(
                SheetRelationshipAnalysis(
                    sheet_name=name,
                    sheet_index=sheet_index.get(name, -1),
                    primary_keys=tuple(pk for pk in primary_keys if pk.column.sheet_name == name),
                    composite_keys=tuple(
                        ck
                        for ck in composite_keys
                        if ck.columns and ck.columns[0].sheet_name == name
                    ),
                )
            )

        # Deduplicate warnings, stable order
        unique_warnings = tuple(dict.fromkeys(warnings))

        return RelationshipAnalysisResult(
            workbook_hash=inspection.file.content_hash,
            inspector_version=inspection.inspector_version,
            region_detector_version=regions.detector_version,
            regions_schema_version=regions.regions_schema_version,
            profiler_version=profiling.profiler_version,
            profiling_schema_version=profiling.profiling_schema_version,
            relationship_engine_version=RELATIONSHIP_ENGINE_VERSION,
            relationship_schema_version=RELATIONSHIP_SCHEMA_VERSION,
            sheets=tuple(sheets),
            foreign_keys=tuple(foreign_keys),
            relationships=tuple(relationships),
            graph=graph,
            warnings=unique_warnings,
            limitations=_LIMITATIONS,
        )
