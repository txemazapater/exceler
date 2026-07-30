"""Workbook inspection domain (Phase 2A) — factual observation only."""

from __future__ import annotations

from exceler.domain.workbook.enums import (
    CellValueKind,
    InspectionWarningCode,
    WorkbookFormat,
    WorksheetVisibility,
)
from exceler.domain.workbook.errors import (
    EncryptedWorkbookError,
    InvalidWorkbookError,
    UnsupportedWorkbookFormatError,
    WorkbookAccessDeniedError,
    WorkbookInspectionError,
    WorkbookLimitExceededError,
    WorkbookNotFoundError,
)
from exceler.domain.workbook.models import (
    CellComment,
    CellInspection,
    CellValue,
    ColumnDimensionInspection,
    DefinedNameInspection,
    ExternalLinkInspection,
    FileIdentity,
    HyperlinkInspection,
    InspectionWarning,
    MergedRangeInspection,
    RelevantCellStyle,
    RowDimensionInspection,
    StructuredTableColumnInspection,
    StructuredTableInspection,
    WorkbookInspection,
    WorkbookInspectionOptions,
    WorksheetInspection,
)

__all__ = [
    "CellComment",
    "CellInspection",
    "CellValue",
    "CellValueKind",
    "ColumnDimensionInspection",
    "DefinedNameInspection",
    "EncryptedWorkbookError",
    "ExternalLinkInspection",
    "FileIdentity",
    "HyperlinkInspection",
    "InspectionWarning",
    "InspectionWarningCode",
    "InvalidWorkbookError",
    "MergedRangeInspection",
    "RelevantCellStyle",
    "RowDimensionInspection",
    "StructuredTableColumnInspection",
    "StructuredTableInspection",
    "UnsupportedWorkbookFormatError",
    "WorkbookAccessDeniedError",
    "WorkbookFormat",
    "WorkbookInspection",
    "WorkbookInspectionError",
    "WorkbookInspectionOptions",
    "WorkbookLimitExceededError",
    "WorkbookNotFoundError",
    "WorksheetInspection",
    "WorksheetVisibility",
]
