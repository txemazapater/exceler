"""Deterministic region profiler — WorkbookInspection + RegionDetectionResult only."""

from __future__ import annotations

from exceler.application.profiling.column_builder import data_row_indices, profile_column
from exceler.domain.profiling.enums import ProfilingStatus
from exceler.domain.profiling.errors import (
    InvalidRegionContractError,
    ProfilingInputMismatchError,
)
from exceler.domain.profiling.models import (
    ProfilingEvidenceItem,
    ProfilingResult,
    RegionProfile,
    SheetProfiles,
)
from exceler.domain.profiling.options import (
    PROFILER_VERSION,
    PROFILING_SCHEMA_VERSION,
    ProfilingOptions,
)
from exceler.domain.regions.models import LogicalRegion, RegionDetectionResult, RegionType
from exceler.domain.workbook.enums import InspectionCompletionStatus
from exceler.domain.workbook.models import CellInspection, WorkbookInspection, WorksheetInspection


def _sheet_cell_index(ws: WorksheetInspection) -> dict[tuple[int, int], CellInspection]:
    return {(cell.row, cell.column): cell for cell in ws.cells}


def _validate_inputs(
    inspection: WorkbookInspection,
    regions: RegionDetectionResult,
) -> None:
    if inspection.file.content_hash != regions.workbook_hash:
        raise ProfilingInputMismatchError(
            "WorkbookInspection.content_hash does not match RegionDetectionResult.workbook_hash."
        )
    sheet_names = {ws.name for ws in inspection.worksheets}
    for sheet in regions.sheets:
        if sheet.sheet_name not in sheet_names:
            raise InvalidRegionContractError(
                f"Region sheet {sheet.sheet_name!r} missing from inspection."
            )
        for region in sheet.regions:
            box = region.bounding_box
            if box.first_row > box.last_row or box.first_col > box.last_col:
                raise InvalidRegionContractError(f"Invalid bounding box on {region.id}")
            for row in (*region.header_row_indices, *region.footer_row_indices):
                if row < box.first_row or row > box.last_row:
                    raise InvalidRegionContractError(
                        f"Header/footer row {row} outside region {region.id}"
                    )


def _is_profileable(region: LogicalRegion, options: ProfilingOptions) -> bool:
    if region.confidence < options.minimum_region_confidence:
        return False
    if region.region_type is RegionType.TABLE:
        return True
    if region.region_type is RegionType.MATRIX:
        return True
    if region.region_type is RegionType.UNKNOWN:
        if not options.include_unknown_regions:
            return False
        box = region.bounding_box
        rows = box.last_row - box.first_row + 1
        cols = box.last_col - box.first_col + 1
        return rows >= options.min_unknown_region_rows and cols >= options.min_unknown_region_cols
    return False


def _profile_region(
    *,
    workbook_hash: str,
    sheet_name: str,
    region: LogicalRegion,
    cell_index: dict[tuple[int, int], CellInspection],
    options: ProfilingOptions,
    inspection_partial: bool,
) -> RegionProfile:
    box = region.bounding_box
    rows = data_row_indices(region, options)
    warnings: list[str] = []
    status = ProfilingStatus.COMPLETE
    if len(rows) < options.minimum_rows_for_inference:
        status = ProfilingStatus.INSUFFICIENT_DATA
        warnings.append("Fewer than minimum_rows_for_inference data rows.")
    if inspection_partial:
        if status is ProfilingStatus.COMPLETE:
            status = ProfilingStatus.PARTIAL
        warnings.append("Underlying inspection was partial.")

    columns = []
    if status is not ProfilingStatus.INSUFFICIENT_DATA or len(rows) > 0:
        for col in range(box.first_col, box.last_col + 1):
            columns.append(
                profile_column(
                    workbook_hash=workbook_hash,
                    sheet_name=sheet_name,
                    region=region,
                    column_index=col,
                    cell_index=cell_index,
                    options=options,
                )
            )

    evidence = (
        ProfilingEvidenceItem(
            "region_profiled",
            region.confidence,
            f"Profiled region type={region.region_type.value}",
        ),
    )
    return RegionProfile(
        region_id=region.id,
        region_type=region.region_type,
        bounding_box=box,
        profiling_status=status,
        row_count=box.last_row - box.first_row + 1,
        data_row_count=len(rows),
        columns=tuple(columns),
        warnings=tuple(warnings),
        evidence=evidence,
    )


class DeterministicRegionProfiler:
    """Pure profiler — never imports or opens Excel files."""

    def profile(
        self,
        inspection: WorkbookInspection,
        regions: RegionDetectionResult,
        options: ProfilingOptions | None = None,
    ) -> ProfilingResult:
        opts = options or ProfilingOptions()
        _validate_inputs(inspection, regions)

        sheets_by_name = {ws.name: ws for ws in inspection.worksheets}
        partial = inspection.completion_status is InspectionCompletionStatus.PARTIAL
        sheet_profiles: list[SheetProfiles] = []
        global_warnings: list[str] = []
        if partial:
            global_warnings.append("Inspection was partial; profiling used observed cells only.")

        for sheet_regions in regions.sheets:
            ws = sheets_by_name[sheet_regions.sheet_name]
            cell_index = _sheet_cell_index(ws)
            region_profiles: list[RegionProfile] = []
            for region in sheet_regions.regions:
                if not _is_profileable(region, opts):
                    continue
                region_profiles.append(
                    _profile_region(
                        workbook_hash=inspection.file.content_hash,
                        sheet_name=ws.name,
                        region=region,
                        cell_index=cell_index,
                        options=opts,
                        inspection_partial=partial,
                    )
                )
            region_profiles.sort(key=lambda item: item.region_id)
            sheet_profiles.append(
                SheetProfiles(
                    sheet_name=ws.name,
                    sheet_index=ws.index,
                    region_profiles=tuple(region_profiles),
                )
            )

        sheet_profiles.sort(key=lambda item: item.sheet_index)
        limitations = (
            "Logical types are structural, not business entities.",
            "Formulas are observed but not evaluated; cached results are unavailable.",
            "Ambiguous locales (e.g. DD/MM vs MM/DD) reduce confidence instead of guessing.",
            "Profiler consumes inspection + regions only; never re-reads Excel.",
            "Identifier/categorical flags are candidates, not primary-key or FK declarations.",
        )
        return ProfilingResult(
            workbook_hash=inspection.file.content_hash,
            inspector_version=inspection.inspector_version,
            region_detector_version=regions.detector_version,
            regions_schema_version=regions.regions_schema_version,
            profiler_version=PROFILER_VERSION,
            profiling_schema_version=PROFILING_SCHEMA_VERSION,
            sheets=tuple(sheet_profiles),
            warnings=tuple(global_warnings),
            limitations=limitations,
        )
