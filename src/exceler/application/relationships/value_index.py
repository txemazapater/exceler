"""Column value extraction from inspection + regions (no Excel)."""

from __future__ import annotations

from dataclasses import dataclass, field

from exceler.application.profiling.column_builder import data_row_indices
from exceler.application.profiling.normalization import normalize_cell
from exceler.domain.profiling.models import ColumnProfile, ProfilingResult, RegionProfile
from exceler.domain.profiling.options import ProfilingOptions
from exceler.domain.regions.models import LogicalRegion, RegionDetectionResult, RegionType
from exceler.domain.relationships.enums import Exactness
from exceler.domain.relationships.models import ColumnRef
from exceler.domain.relationships.options import RelationshipOptions
from exceler.domain.workbook.models import CellInspection, WorkbookInspection, WorksheetInspection


@dataclass
class ColumnValueSet:
    ref: ColumnRef
    profile: ColumnProfile
    region: LogicalRegion
    # Parallel row-aligned values (None = null/blank/formula/error/unobserved)
    row_values: list[str | None]
    distinct: set[str]
    content_count: int
    nullish_count: int
    exactness: Exactness
    warnings: list[str] = field(default_factory=list)


def _sheet_index(ws: WorksheetInspection) -> dict[tuple[int, int], CellInspection]:
    return {(cell.row, cell.column): cell for cell in ws.cells}


def _profile_options(options: RelationshipOptions) -> ProfilingOptions:
    return ProfilingOptions(
        exclude_header_rows=options.exclude_header_rows,
        exclude_footer_rows=options.exclude_footer_rows,
        trim_strings_for_analysis=options.trim_values,
        case_sensitive_cardinality=options.case_sensitive_values,
    )


def build_column_value_sets(
    inspection: WorkbookInspection,
    regions: RegionDetectionResult,
    profiling: ProfilingResult,
    options: RelationshipOptions,
) -> list[ColumnValueSet]:
    """Rebuild per-column value sets from inspection cells (full sets, not profile samples)."""
    ws_by_name = {ws.name: ws for ws in inspection.worksheets}
    region_by_id: dict[str, LogicalRegion] = {}
    for sheet in regions.sheets:
        for region in sheet.regions:
            region_by_id[region.id] = region

    cell_indexes = {name: _sheet_index(ws) for name, ws in ws_by_name.items()}
    profile_opts = _profile_options(options)
    results: list[ColumnValueSet] = []

    for sheet_prof in profiling.sheets:
        ws = ws_by_name.get(sheet_prof.sheet_name)
        if ws is None:
            continue
        cell_index = cell_indexes[sheet_prof.sheet_name]
        for region_prof in sheet_prof.region_profiles:
            maybe_region = region_by_id.get(region_prof.region_id)
            if maybe_region is None:
                continue
            region = maybe_region
            if region.region_type not in {RegionType.TABLE, RegionType.MATRIX, RegionType.UNKNOWN}:
                continue
            rows = data_row_indices(region, profile_opts)
            for col in region_prof.columns:
                results.append(
                    _extract_column(
                        region=region,
                        region_prof=region_prof,
                        column=col,
                        rows=rows,
                        cell_index=cell_index,
                        options=options,
                    )
                )
    return results


def _extract_column(
    *,
    region: LogicalRegion,
    region_prof: RegionProfile,
    column: ColumnProfile,
    rows: list[int],
    cell_index: dict[tuple[int, int], CellInspection],
    options: RelationshipOptions,
) -> ColumnValueSet:
    ref = ColumnRef(
        column_id=column.id,
        sheet_name=column.sheet_name,
        region_id=column.region_id,
        column_index=column.column_index,
        column_letter=column.column_letter,
        effective_name=column.effective_name,
    )
    row_values: list[str | None] = []
    distinct: set[str] = set()
    content_count = 0
    nullish_count = 0
    truncated = False
    warnings: list[str] = []
    formula_count = 0

    for row in rows:
        cell = cell_index.get((row, column.column_index))
        norm = normalize_cell(cell, trim=options.trim_values)
        if norm.is_formula:
            formula_count += 1
            row_values.append(None)
            nullish_count += 1
            continue
        if norm.is_error or not norm.has_content:
            row_values.append(None)
            nullish_count += 1
            continue
        value = norm.trimmed if options.trim_values else norm.original
        if value is None:
            row_values.append(None)
            nullish_count += 1
            continue
        if not options.case_sensitive_values:
            value = value.casefold()
        row_values.append(value)
        content_count += 1
        if len(distinct) >= options.max_distinct_values_tracked and value not in distinct:
            truncated = True
            continue
        distinct.add(value)

    if formula_count:
        warnings.append(f"Excluded {formula_count} formula cell(s) from key domain.")
    if truncated:
        warnings.append("Distinct value set truncated; inclusion metrics may be incomplete.")

    return ColumnValueSet(
        ref=ref,
        profile=column,
        region=region,
        row_values=row_values,
        distinct=distinct,
        content_count=content_count,
        nullish_count=nullish_count,
        exactness=Exactness.TRUNCATED if truncated else Exactness.EXACT,
        warnings=warnings,
    )
