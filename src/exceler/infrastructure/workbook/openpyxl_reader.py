"""OpenPyxl adapter for factual workbook inspection (Phase 2A).

Open options (documented):
- data_only=False — preserve formula expressions; never evaluate.
- keep_vba=False — do not load VBA for execution; VBA presence is detected via ZIP.
- keep_links=True — retain external link metadata if present (never followed/downloaded).
- read_only=False — full load so tables, dimensions, merges and styles are observable.
"""

from __future__ import annotations

import logging
import time
import uuid
import zipfile
from datetime import UTC, date, datetime
from datetime import time as time_cls
from decimal import Decimal
from io import BytesIO
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from exceler.application.workbook.ports import WorkbookSource
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
    WorkbookLimitExceededError,
)
from exceler.domain.workbook.models import (
    INSPECTOR_VERSION,
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

logger = logging.getLogger("exceler.workbook.inspection")


def _has_vba_project(payload: bytes) -> bool:
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            return any(name.lower().endswith("vbaproject.bin") for name in archive.namelist())
    except zipfile.BadZipFile:
        return False


def _map_visibility(state: str | None) -> WorksheetVisibility:
    if state == "hidden":
        return WorksheetVisibility.HIDDEN
    if state == "veryHidden":
        return WorksheetVisibility.VERY_HIDDEN
    return WorksheetVisibility.VISIBLE


def _map_value(raw: Any, *, library_data_type: str | None) -> CellValue:
    if raw is None:
        return CellValue(kind=CellValueKind.NULL)
    if isinstance(raw, bool):
        return CellValue(kind=CellValueKind.BOOLEAN, boolean=raw)
    if isinstance(raw, int) and not isinstance(raw, bool):
        return CellValue(kind=CellValueKind.INTEGER, integer=raw)
    if isinstance(raw, float):
        return CellValue(kind=CellValueKind.DECIMAL, decimal=format(Decimal(str(raw)), "f"))
    if isinstance(raw, Decimal):
        return CellValue(kind=CellValueKind.DECIMAL, decimal=format(raw, "f"))
    if isinstance(raw, datetime):
        return CellValue(kind=CellValueKind.DATETIME, datetime=raw.isoformat())
    if isinstance(raw, date):
        return CellValue(kind=CellValueKind.DATE, date=raw.isoformat())
    if isinstance(raw, time_cls):
        return CellValue(kind=CellValueKind.TIME, time=raw.isoformat())
    if library_data_type == "e" or (
        isinstance(raw, str) and raw.startswith("#") and raw.endswith("!")
    ):
        return CellValue(kind=CellValueKind.ERROR, error=str(raw))
    if isinstance(raw, str):
        return CellValue(kind=CellValueKind.STRING, text=raw)
    return CellValue(kind=CellValueKind.STRING, text=str(raw))


def _cell_relevant(cell: Any, *, options: WorkbookInspectionOptions) -> bool:
    if cell.value is not None:
        return True
    if options.include_comments and cell.comment is not None:
        return True
    if options.include_hyperlinks and cell.hyperlink is not None:
        return True
    if cell.data_type == "f":
        return True
    if options.include_empty_formatted_cells:
        if cell.number_format not in (None, "General"):
            return True
        if cell.font is not None and cell.font.bold:
            return True
    return False


class OpenPyxlWorkbookReader:
    def inspect(
        self,
        source: WorkbookSource,
        options: WorkbookInspectionOptions | None = None,
    ) -> WorkbookInspection:
        opts = options or WorkbookInspectionOptions()
        started = time.perf_counter()
        inspected_at = datetime.now(tz=UTC)
        inspection_id = str(uuid.uuid4())

        logger.info(
            "inspection_started",
            extra={
                "event": "inspection_started",
                "file_name": source.name,
                "inspection_id": inspection_id,
            },
        )

        size = source.size_bytes()
        if size > opts.max_file_size_bytes:
            raise WorkbookLimitExceededError(
                f"Workbook exceeds max_file_size_bytes ({opts.max_file_size_bytes})."
            )
        if size == 0:
            raise InvalidWorkbookError("Workbook file is empty.")

        extension = source.suggested_extension.lstrip(".").lower()
        if extension not in {"xlsx", "xlsm"}:
            raise UnsupportedWorkbookFormatError(
                f"Unsupported workbook format: {extension or 'unknown'}"
            )
        workbook_format = WorkbookFormat.XLSM if extension == "xlsm" else WorkbookFormat.XLSX

        try:
            with source.open_binary() as handle:
                payload = handle.read()
        except Exception:
            raise

        content_hash = source.content_hash()
        has_vba = _has_vba_project(payload)
        warnings: list[InspectionWarning] = []
        limitations: list[str] = [
            "Formulas are observed, not evaluated (data_only=False).",
            "VBA projects are detected by ZIP presence only; never executed.",
            "External links are listed when present; never followed or downloaded.",
            "Document core/custom properties are not required for Phase 2A.",
        ]

        if has_vba:
            warnings.append(
                InspectionWarning(
                    code=InspectionWarningCode.VBA_PROJECT_PRESENT,
                    message="Workbook package contains vbaProject.bin (not executed).",
                )
            )

        try:
            # data_only=False: preserve formulas.
            # keep_vba=False: never load VBA for execution.
            # keep_links=True: retain link metadata without network access.
            wb = load_workbook(
                BytesIO(payload),
                read_only=False,
                data_only=False,
                keep_vba=False,
                keep_links=True,
            )
        except InvalidFileException as exc:
            message = str(exc).lower()
            if "olecf" in message or "encrypted" in message or "password" in message:
                raise EncryptedWorkbookError() from exc
            raise InvalidWorkbookError() from exc
        except zipfile.BadZipFile as exc:
            raise InvalidWorkbookError() from exc
        except KeyError as exc:
            raise InvalidWorkbookError() from exc
        except Exception as exc:  # noqa: BLE001
            raise InvalidWorkbookError() from exc

        logger.debug(
            "workbook_opened",
            extra={
                "event": "workbook_opened",
                "inspection_id": inspection_id,
                "format": workbook_format.value,
                "sheet_count": len(wb.sheetnames),
                "size_bytes": size,
            },
        )

        if len(wb.sheetnames) > opts.max_worksheets:
            wb.close()
            raise WorkbookLimitExceededError(
                f"Workbook exceeds max_worksheets ({opts.max_worksheets})."
            )

        worksheets: list[WorksheetInspection] = []
        cells_observed = 0
        cell_budget = opts.max_cells

        for index, name in enumerate(wb.sheetnames):
            ws = wb[name]
            sheet_inspection, used = self._inspect_worksheet(
                ws,
                index=index,
                options=opts,
                cell_budget=cell_budget,
                warnings=warnings,
            )
            worksheets.append(sheet_inspection)
            cells_observed += used
            cell_budget -= used
            logger.debug(
                "worksheet_inspected",
                extra={
                    "event": "worksheet_inspected",
                    "inspection_id": inspection_id,
                    "sheet": name,
                    "cells_observed": used,
                },
            )
            if cell_budget <= 0 and index < len(wb.sheetnames) - 1:
                warnings.append(
                    InspectionWarning(
                        code=InspectionWarningCode.CELL_LIMIT_REACHED,
                        message="max_cells reached; remaining worksheets partially skipped.",
                    )
                )
                logger.warning(
                    "inspection_limit_reached",
                    extra={"event": "inspection_limit_reached", "inspection_id": inspection_id},
                )
                break

        defined_names = tuple(
            sorted(
                (
                    DefinedNameInspection(
                        name=key,
                        attr_text=getattr(wb.defined_names[key], "attr_text", None),
                        local_sheet_id=getattr(wb.defined_names[key], "localSheetId", None),
                    )
                    for key in wb.defined_names.keys()
                ),
                key=lambda item: (item.local_sheet_id is not None, item.name),
            )
        )

        external_links: list[ExternalLinkInspection] = []
        if opts.include_external_links:
            for link in getattr(wb, "_external_links", None) or []:
                target = getattr(getattr(link, "file_link", None), "Target", None)
                external_links.append(ExternalLinkInspection(target=str(target or link)))
            if external_links:
                warnings.append(
                    InspectionWarning(
                        code=InspectionWarningCode.EXTERNAL_LINK_PRESENT,
                        message="Workbook declares external links (not followed).",
                    )
                )

        wb.close()

        modified_at = None
        modified_iso = source.modified_at_iso()
        if modified_iso:
            modified_at = datetime.fromisoformat(modified_iso)

        duration_ms = int((time.perf_counter() - started) * 1000)
        result = WorkbookInspection(
            inspection_id=inspection_id,
            inspector_version=INSPECTOR_VERSION,
            inspected_at=inspected_at,
            duration_ms=duration_ms,
            format=workbook_format,
            file=FileIdentity(
                source_path=source.source_path(),
                file_name=source.name,
                extension=extension,
                size_bytes=size,
                modified_at=modified_at,
                content_hash=content_hash,
            ),
            worksheets=tuple(worksheets),
            defined_names=defined_names,
            external_links=tuple(sorted(external_links, key=lambda item: item.target)),
            has_vba_project=has_vba,
            warnings=tuple(warnings),
            limitations=tuple(limitations),
            cells_observed=cells_observed,
            worksheets_observed=len(worksheets),
        )
        logger.info(
            "inspection_completed",
            extra={
                "event": "inspection_completed",
                "inspection_id": inspection_id,
                "duration_ms": duration_ms,
                "cells_observed": cells_observed,
                "worksheets_observed": len(worksheets),
                "has_vba_project": has_vba,
            },
        )
        return result

    def _inspect_worksheet(
        self,
        ws: Any,
        *,
        index: int,
        options: WorkbookInspectionOptions,
        cell_budget: int,
        warnings: list[InspectionWarning],
    ) -> tuple[WorksheetInspection, int]:
        declared = None
        try:
            declared = ws.calculate_dimension()
        except Exception:  # noqa: BLE001
            declared = None

        auto_filter = None
        if ws.auto_filter is not None and ws.auto_filter.ref:
            auto_filter = ws.auto_filter.ref

        merged: list[MergedRangeInspection] = []
        for rng in sorted(str(r) for r in ws.merged_cells.ranges):
            anchor = rng.split(":")[0]
            cell = ws[anchor]
            raw = cell.value
            if isinstance(raw, str) and raw.startswith("="):
                value = CellValue(kind=CellValueKind.NULL)
            else:
                value = _map_value(raw, library_data_type=getattr(cell, "data_type", None))
            merged.append(MergedRangeInspection(reference=rng, anchor=anchor, anchor_value=value))

        row_dims: list[RowDimensionInspection] = []
        for idx, dim in sorted(ws.row_dimensions.items(), key=lambda item: int(item[0])):
            if dim.hidden or dim.height is not None:
                row_dims.append(
                    RowDimensionInspection(
                        index=int(idx),
                        hidden=bool(dim.hidden),
                        height=float(dim.height) if dim.height is not None else None,
                    )
                )

        col_dims: list[ColumnDimensionInspection] = []
        for letter, dim in sorted(ws.column_dimensions.items()):
            if dim.hidden or dim.width is not None:
                col_dims.append(
                    ColumnDimensionInspection(
                        letter=letter,
                        hidden=bool(dim.hidden),
                        width=float(dim.width) if dim.width is not None else None,
                    )
                )

        tables: list[StructuredTableInspection] = []
        for name in sorted(ws.tables.keys()):
            table = ws.tables[name]
            columns: list[StructuredTableColumnInspection] = []
            table_columns = getattr(table, "tableColumns", None)
            if table_columns is not None:
                for col_index, col in enumerate(list(table_columns)):
                    columns.append(
                        StructuredTableColumnInspection(
                            name=getattr(col, "name", f"Column{col_index + 1}"),
                            index=col_index,
                        )
                    )
            auto = None
            if table.autoFilter is not None:
                auto = table.autoFilter.ref
            tables.append(
                StructuredTableInspection(
                    name=name,
                    display_name=table.displayName,
                    reference=table.ref,
                    header_row_count=int(table.headerRowCount or 0),
                    totals_row_count=int(table.totalsRowCount or 0),
                    auto_filter=auto,
                    columns=tuple(columns),
                )
            )

        cells: list[CellInspection] = []
        max_row = ws.max_row or 1
        max_col = ws.max_column or 1
        used = 0
        for row in ws.iter_rows(min_row=1, max_row=max_row, max_col=max_col):
            for cell in row:
                if not _cell_relevant(cell, options=options):
                    continue
                if used >= cell_budget:
                    warnings.append(
                        InspectionWarning(
                            code=InspectionWarningCode.CELL_LIMIT_REACHED,
                            message="max_cells reached while reading worksheet cells.",
                            location=ws.title,
                        )
                    )
                    break
                formula = None
                raw = cell.value
                if isinstance(raw, str) and raw.startswith("="):
                    formula = raw
                    value = CellValue(kind=CellValueKind.NULL)
                elif cell.data_type == "f" and raw is not None:
                    formula = str(raw)
                    value = CellValue(kind=CellValueKind.NULL)
                else:
                    value = _map_value(raw, library_data_type=cell.data_type)
                comment = None
                if options.include_comments and cell.comment is not None:
                    comment = CellComment(text=cell.comment.text, author=cell.comment.author)
                hyperlink = None
                if options.include_hyperlinks and cell.hyperlink is not None:
                    hyperlink = HyperlinkInspection(
                        target=cell.hyperlink.target,
                        tooltip=getattr(cell.hyperlink, "tooltip", None),
                    )
                style = None
                bold = bool(cell.font and cell.font.bold)
                if bold or (cell.number_format not in (None, "General")):
                    style = RelevantCellStyle(
                        font_bold=bold,
                        number_format=cell.number_format,
                    )
                cells.append(
                    CellInspection(
                        coordinate=cell.coordinate,
                        row=cell.row,
                        column=cell.column,
                        value=value,
                        library_data_type=cell.data_type,
                        number_format=cell.number_format,
                        formula=formula,
                        comment=comment,
                        hyperlink=hyperlink,
                        style=style,
                    )
                )
                used += 1
            else:
                continue
            break

        cells.sort(key=lambda item: (item.row, item.column))

        # Inflated dimension heuristic: declared span >> cells with values/formulas.
        if declared and ":" in declared:
            valued_rows = [
                c.row for c in cells if c.formula is not None or c.value.kind.value != "null"
            ]
            valued_cols = [
                c.column for c in cells if c.formula is not None or c.value.kind.value != "null"
            ]
            last_row = max(valued_rows, default=1)
            last_col = max(valued_cols, default=1)
            if max_row > last_row * 5 + 50 or max_col > last_col * 5 + 10:
                warnings.append(
                    InspectionWarning(
                        code=InspectionWarningCode.DIMENSION_MAY_BE_INFLATED,
                        message=(
                            "Worksheet declared_dimension appears larger than "
                            "observed valued cells."
                        ),
                        location=ws.title,
                    )
                )

        return (
            WorksheetInspection(
                name=ws.title,
                index=index,
                visibility=_map_visibility(ws.sheet_state),
                declared_dimension=declared,
                freeze_panes=ws.freeze_panes,
                auto_filter=auto_filter,
                merged_ranges=tuple(merged),
                row_dimensions=tuple(row_dims),
                column_dimensions=tuple(col_dims),
                tables=tuple(tables),
                cells=tuple(cells),
                cells_observed=used,
            ),
            used,
        )
