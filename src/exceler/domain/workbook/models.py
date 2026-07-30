from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from exceler.domain.workbook.enums import (
    CellValueKind,
    InspectionWarningCode,
    WorkbookFormat,
    WorksheetVisibility,
)

INSPECTOR_VERSION = "2A.1"
INSPECTION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class WorkbookInspectionOptions:
    include_empty_formatted_cells: bool = True
    include_comments: bool = True
    include_hyperlinks: bool = True
    include_external_links: bool = True
    max_worksheets: int = 1_000
    max_cells: int = 2_000_000
    max_file_size_bytes: int = 512 * 1024 * 1024  # 512 MiB pathological guard


@dataclass(frozen=True)
class FileIdentity:
    """Neutral file identity — not a full AssetSnapshot (Phase 2S/3)."""

    source_path: str | None
    file_name: str
    extension: str
    size_bytes: int
    modified_at: datetime | None
    content_hash: str


@dataclass(frozen=True)
class CellValue:
    kind: CellValueKind
    text: str | None = None
    integer: int | None = None
    decimal: str | None = None
    boolean: bool | None = None
    date: str | None = None
    datetime: str | None = None
    time: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"kind": self.kind.value}
        if self.kind is CellValueKind.NULL:
            return payload
        if self.text is not None:
            payload["text"] = self.text
        if self.integer is not None:
            payload["integer"] = self.integer
        if self.decimal is not None:
            payload["decimal"] = self.decimal
        if self.boolean is not None:
            payload["boolean"] = self.boolean
        if self.date is not None:
            payload["date"] = self.date
        if self.datetime is not None:
            payload["datetime"] = self.datetime
        if self.time is not None:
            payload["time"] = self.time
        if self.error is not None:
            payload["error"] = self.error
        return payload


@dataclass(frozen=True)
class CellComment:
    text: str
    author: str | None = None


@dataclass(frozen=True)
class HyperlinkInspection:
    target: str | None
    tooltip: str | None = None


@dataclass(frozen=True)
class RelevantCellStyle:
    font_bold: bool = False
    number_format: str | None = None


@dataclass(frozen=True)
class CellInspection:
    coordinate: str
    row: int
    column: int
    value: CellValue
    library_data_type: str | None
    number_format: str | None
    formula: str | None
    comment: CellComment | None
    hyperlink: HyperlinkInspection | None
    style: RelevantCellStyle | None


@dataclass(frozen=True)
class MergedRangeInspection:
    reference: str
    anchor: str
    anchor_value: CellValue | None


@dataclass(frozen=True)
class RowDimensionInspection:
    index: int
    hidden: bool
    height: float | None


@dataclass(frozen=True)
class ColumnDimensionInspection:
    letter: str
    hidden: bool
    width: float | None


@dataclass(frozen=True)
class StructuredTableColumnInspection:
    name: str
    index: int


@dataclass(frozen=True)
class StructuredTableInspection:
    name: str
    display_name: str
    reference: str
    header_row_count: int
    totals_row_count: int
    auto_filter: str | None
    columns: tuple[StructuredTableColumnInspection, ...]


@dataclass(frozen=True)
class DefinedNameInspection:
    name: str
    attr_text: str | None
    local_sheet_id: int | None


@dataclass(frozen=True)
class ExternalLinkInspection:
    target: str


@dataclass(frozen=True)
class InspectionWarning:
    code: InspectionWarningCode
    message: str
    location: str | None = None


@dataclass(frozen=True)
class WorksheetInspection:
    name: str
    index: int
    visibility: WorksheetVisibility
    declared_dimension: str | None
    freeze_panes: str | None
    auto_filter: str | None
    merged_ranges: tuple[MergedRangeInspection, ...]
    row_dimensions: tuple[RowDimensionInspection, ...]
    column_dimensions: tuple[ColumnDimensionInspection, ...]
    tables: tuple[StructuredTableInspection, ...]
    cells: tuple[CellInspection, ...]
    cells_observed: int


@dataclass(frozen=True)
class WorkbookInspection:
    inspection_id: str
    inspector_version: str
    inspected_at: datetime
    duration_ms: int
    format: WorkbookFormat
    file: FileIdentity
    worksheets: tuple[WorksheetInspection, ...]
    defined_names: tuple[DefinedNameInspection, ...]
    external_links: tuple[ExternalLinkInspection, ...]
    has_vba_project: bool
    warnings: tuple[InspectionWarning, ...]
    limitations: tuple[str, ...] = field(default_factory=tuple)
    cells_observed: int = 0
    worksheets_observed: int = 0
