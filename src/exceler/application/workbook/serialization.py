from __future__ import annotations

from typing import Any

from exceler.domain.workbook.models import (
    INSPECTION_SCHEMA_VERSION,
    CellInspection,
    CellValue,
    WorkbookInspection,
    WorksheetInspection,
)


def cell_value_to_dict(value: CellValue) -> dict[str, Any]:
    return value.to_dict()


def cell_to_dict(cell: CellInspection) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "coordinate": cell.coordinate,
        "row": cell.row,
        "column": cell.column,
        "value": cell_value_to_dict(cell.value),
        "library_data_type": cell.library_data_type,
        "number_format": cell.number_format,
        "formula": cell.formula,
    }
    if cell.comment is not None:
        payload["comment"] = {"text": cell.comment.text, "author": cell.comment.author}
    if cell.hyperlink is not None:
        payload["hyperlink"] = {
            "target": cell.hyperlink.target,
            "tooltip": cell.hyperlink.tooltip,
        }
    if cell.style is not None:
        style_payload: dict[str, Any] = {
            "font_bold": cell.style.font_bold,
            "number_format": cell.style.number_format,
        }
        if cell.style.font_name is not None:
            style_payload["font_name"] = cell.style.font_name
        if cell.style.font_size is not None:
            style_payload["font_size"] = cell.style.font_size
        if cell.style.font_color is not None:
            style_payload["font_color"] = cell.style.font_color
        if cell.style.fill_color is not None:
            style_payload["fill_color"] = cell.style.fill_color
        if cell.style.horizontal_alignment is not None:
            style_payload["horizontal_alignment"] = cell.style.horizontal_alignment
        style_payload["border_top"] = cell.style.border_top
        style_payload["border_right"] = cell.style.border_right
        style_payload["border_bottom"] = cell.style.border_bottom
        style_payload["border_left"] = cell.style.border_left
        payload["style"] = style_payload
    return payload


def worksheet_to_dict(ws: WorksheetInspection) -> dict[str, Any]:
    return {
        "name": ws.name,
        "index": ws.index,
        "visibility": ws.visibility.value,
        "declared_dimension": ws.declared_dimension,
        "freeze_panes": ws.freeze_panes,
        "auto_filter": ws.auto_filter,
        "merged_ranges": [
            {
                "reference": item.reference,
                "anchor": item.anchor,
                "anchor_value": (
                    cell_value_to_dict(item.anchor_value) if item.anchor_value else None
                ),
            }
            for item in ws.merged_ranges
        ],
        "row_dimensions": [
            {"index": item.index, "hidden": item.hidden, "height": item.height}
            for item in ws.row_dimensions
        ],
        "column_dimensions": [
            {"letter": item.letter, "hidden": item.hidden, "width": item.width}
            for item in ws.column_dimensions
        ],
        "tables": [
            {
                "name": table.name,
                "display_name": table.display_name,
                "reference": table.reference,
                "header_row_count": table.header_row_count,
                "totals_row_count": table.totals_row_count,
                "auto_filter": table.auto_filter,
                "columns": [{"name": col.name, "index": col.index} for col in table.columns],
            }
            for table in ws.tables
        ],
        "cells": [cell_to_dict(cell) for cell in ws.cells],
        "cells_observed": ws.cells_observed,
        "cells_scanned": ws.cells_scanned,
    }


def inspection_to_dict(
    inspection: WorkbookInspection,
    *,
    include_ephemeral: bool = True,
) -> dict[str, Any]:
    """Serialize inspection. Ephemeral fields can be omitted for determinism tests."""
    payload: dict[str, Any] = {
        "schema_version": INSPECTION_SCHEMA_VERSION,
        "inspection": {
            "inspector_version": inspection.inspector_version,
            "format": inspection.format.value,
            "completion_status": inspection.completion_status.value,
            "truncation_reasons": [
                {
                    "code": item.code.value,
                    "message": item.message,
                    "location": item.location,
                }
                for item in inspection.truncation_reasons
            ],
            "file": {
                "file_name": inspection.file.file_name,
                "extension": inspection.file.extension,
                "size_bytes": inspection.file.size_bytes,
                "content_hash": inspection.file.content_hash,
                "source_path": inspection.file.source_path,
                "modified_at": (
                    inspection.file.modified_at.isoformat() if inspection.file.modified_at else None
                ),
            },
            "has_vba_project": inspection.has_vba_project,
            "worksheets": [worksheet_to_dict(ws) for ws in inspection.worksheets],
            "defined_names": [
                {
                    "name": item.name,
                    "attr_text": item.attr_text,
                    "local_sheet_id": item.local_sheet_id,
                }
                for item in inspection.defined_names
            ],
            "external_links": [{"target": item.target} for item in inspection.external_links],
            "warnings": [
                {
                    "code": warning.code.value,
                    "message": warning.message,
                    "location": warning.location,
                }
                for warning in inspection.warnings
            ],
            "limitations": list(inspection.limitations),
            "cells_observed": inspection.cells_observed,
            "cells_scanned": inspection.cells_scanned,
            "worksheets_observed": inspection.worksheets_observed,
            "duration_ms": inspection.duration_ms,
        },
    }
    if include_ephemeral:
        payload["inspection"]["inspection_id"] = inspection.inspection_id
        payload["inspection"]["inspected_at"] = inspection.inspected_at.isoformat()
    return payload


def deterministic_inspection_dict(inspection: WorkbookInspection) -> dict[str, Any]:
    data = inspection_to_dict(inspection, include_ephemeral=False)
    file_meta = data["inspection"]["file"]
    file_meta.pop("source_path", None)
    file_meta.pop("modified_at", None)
    data["inspection"].pop("duration_ms", None)
    return data
