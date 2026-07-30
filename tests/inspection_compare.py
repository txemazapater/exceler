"""Partial expectation comparator for Phase 2A inspection contracts."""

from __future__ import annotations

from typing import Any

from exceler.domain.workbook.models import WorkbookInspection


class ExpectationMismatchError(AssertionError):
    def __init__(self, scenario_id: str, path: str, expected: Any, actual: Any) -> None:
        super().__init__(
            f"Scenario: {scenario_id}\nPath: {path}\nExpected: {expected!r}\nActual: {actual!r}"
        )
        self.scenario_id = scenario_id
        self.path = path
        self.expected = expected
        self.actual = actual


def _find_worksheet(inspection: WorkbookInspection, name: str | None, index: int | None):
    if name is not None:
        for ws in inspection.worksheets:
            if ws.name == name:
                return ws
        return None
    if index is not None and 0 <= index < len(inspection.worksheets):
        return inspection.worksheets[index]
    return None


def _find_cell(inspection: WorkbookInspection, sheet: str, coordinate: str):
    ws = _find_worksheet(inspection, sheet, None)
    if ws is None:
        return None
    for cell in ws.cells:
        if cell.coordinate == coordinate:
            return cell
    return None


def compare_inspection_expectations(
    *,
    scenario_id: str,
    inspection: WorkbookInspection,
    expected: dict[str, Any],
) -> None:
    """Compare partial expectations.inspection against an inspection result."""
    if not expected:
        return

    workbook_exp = expected.get("workbook")
    if isinstance(workbook_exp, dict):
        if "format" in workbook_exp and workbook_exp["format"] != inspection.format.value:
            raise ExpectationMismatchError(
                scenario_id,
                "expectations.inspection.workbook.format",
                workbook_exp["format"],
                inspection.format.value,
            )
        if (
            "has_vba_project" in workbook_exp
            and workbook_exp["has_vba_project"] != inspection.has_vba_project
        ):
            raise ExpectationMismatchError(
                scenario_id,
                "expectations.inspection.workbook.has_vba_project",
                workbook_exp["has_vba_project"],
                inspection.has_vba_project,
            )
        if "worksheet_count" in workbook_exp and workbook_exp["worksheet_count"] != len(
            inspection.worksheets
        ):
            raise ExpectationMismatchError(
                scenario_id,
                "expectations.inspection.workbook.worksheet_count",
                workbook_exp["worksheet_count"],
                len(inspection.worksheets),
            )

    warning_codes = {w.code.value for w in inspection.warnings}
    for code in expected.get("warnings_contain") or []:
        if code not in warning_codes:
            raise ExpectationMismatchError(
                scenario_id,
                "expectations.inspection.warnings_contain",
                code,
                sorted(warning_codes),
            )

    for idx, ws_exp in enumerate(expected.get("worksheets") or []):
        ws = _find_worksheet(inspection, ws_exp.get("name"), ws_exp.get("index", idx))
        path = f"expectations.inspection.worksheets[{idx}]"
        if ws is None:
            raise ExpectationMismatchError(scenario_id, path, ws_exp, None)
        if "name" in ws_exp and ws.name != ws_exp["name"]:
            raise ExpectationMismatchError(scenario_id, f"{path}.name", ws_exp["name"], ws.name)
        if "index" in ws_exp and ws.index != ws_exp["index"]:
            raise ExpectationMismatchError(scenario_id, f"{path}.index", ws_exp["index"], ws.index)
        if "visibility" in ws_exp and ws.visibility.value != ws_exp["visibility"]:
            raise ExpectationMismatchError(
                scenario_id, f"{path}.visibility", ws_exp["visibility"], ws.visibility.value
            )
        if "freeze_panes" in ws_exp and ws.freeze_panes != ws_exp["freeze_panes"]:
            raise ExpectationMismatchError(
                scenario_id, f"{path}.freeze_panes", ws_exp["freeze_panes"], ws.freeze_panes
            )
        if "auto_filter" in ws_exp and ws.auto_filter != ws_exp["auto_filter"]:
            raise ExpectationMismatchError(
                scenario_id, f"{path}.auto_filter", ws_exp["auto_filter"], ws.auto_filter
            )
        if "hidden_columns" in ws_exp:
            actual_hidden = [c.letter for c in ws.column_dimensions if c.hidden]
            if actual_hidden != ws_exp["hidden_columns"]:
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{path}.hidden_columns",
                    ws_exp["hidden_columns"],
                    actual_hidden,
                )
        if "hidden_rows" in ws_exp:
            actual_hidden_rows = [r.index for r in ws.row_dimensions if r.hidden]
            if actual_hidden_rows != ws_exp["hidden_rows"]:
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{path}.hidden_rows",
                    ws_exp["hidden_rows"],
                    actual_hidden_rows,
                )
        if "merged_ranges" in ws_exp:
            actual_merged = [m.reference for m in ws.merged_ranges]
            if actual_merged != ws_exp["merged_ranges"]:
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{path}.merged_ranges",
                    ws_exp["merged_ranges"],
                    actual_merged,
                )
        if "tables" in ws_exp:
            by_name = {t.name: t for t in ws.tables}
            for t_idx, table_exp in enumerate(ws_exp["tables"]):
                table = by_name.get(table_exp["name"])
                tpath = f"{path}.tables[{t_idx}]"
                if table is None:
                    raise ExpectationMismatchError(scenario_id, tpath, table_exp, None)
                if "ref" in table_exp and table.reference != table_exp["ref"]:
                    raise ExpectationMismatchError(
                        scenario_id, f"{tpath}.ref", table_exp["ref"], table.reference
                    )
                if (
                    "totals_row_count" in table_exp
                    and table.totals_row_count != table_exp["totals_row_count"]
                ):
                    raise ExpectationMismatchError(
                        scenario_id,
                        f"{tpath}.totals_row_count",
                        table_exp["totals_row_count"],
                        table.totals_row_count,
                    )
        if "min_observed_cells" in ws_exp and ws.cells_observed < ws_exp["min_observed_cells"]:
            raise ExpectationMismatchError(
                scenario_id,
                f"{path}.min_observed_cells",
                f">={ws_exp['min_observed_cells']}",
                ws.cells_observed,
            )
        if ws_exp.get("declared_dimension_inflated"):
            if "DIMENSION_MAY_BE_INFLATED" not in warning_codes:
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{path}.declared_dimension_inflated",
                    True,
                    False,
                )

    for idx, name_exp in enumerate(expected.get("defined_names") or []):
        actual = next((n for n in inspection.defined_names if n.name == name_exp["name"]), None)
        path = f"expectations.inspection.defined_names[{idx}]"
        if actual is None:
            raise ExpectationMismatchError(scenario_id, path, name_exp, None)
        if "local_sheet_id" in name_exp and actual.local_sheet_id != name_exp["local_sheet_id"]:
            raise ExpectationMismatchError(
                scenario_id,
                f"{path}.local_sheet_id",
                name_exp["local_sheet_id"],
                actual.local_sheet_id,
            )

    for idx, cell_exp in enumerate(expected.get("cells") or []):
        cell = _find_cell(inspection, cell_exp["sheet"], cell_exp["coordinate"])
        path = f"expectations.inspection.cells[{idx}]"
        if cell is None:
            raise ExpectationMismatchError(scenario_id, path, cell_exp, None)
        if "formula" in cell_exp and cell.formula != cell_exp["formula"]:
            raise ExpectationMismatchError(
                scenario_id, f"{path}.formula", cell_exp["formula"], cell.formula
            )
        if "value_kind" in cell_exp and cell.value.kind.value != cell_exp["value_kind"]:
            raise ExpectationMismatchError(
                scenario_id,
                f"{path}.value_kind",
                cell_exp["value_kind"],
                cell.value.kind.value,
            )
        if "text" in cell_exp and cell.value.text != cell_exp["text"]:
            raise ExpectationMismatchError(
                scenario_id, f"{path}.text", cell_exp["text"], cell.value.text
            )
        if cell_exp.get("has_comment") and cell.comment is None:
            raise ExpectationMismatchError(scenario_id, f"{path}.has_comment", True, False)
        if cell_exp.get("has_hyperlink") and cell.hyperlink is None:
            raise ExpectationMismatchError(scenario_id, f"{path}.has_hyperlink", True, False)
