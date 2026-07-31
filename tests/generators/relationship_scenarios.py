"""Phase 2D relationship / key synthetic scenarios."""

from __future__ import annotations

from openpyxl import Workbook
from openpyxl.styles import Font
from tests.generators.workbook_factory import ScenarioSpec, bold_header, new_workbook, write_matrix


def build_rel_simple_primary_key(_seed: int) -> Workbook:
    wb = new_workbook(sheet_title="Customers")
    ws = wb.active
    assert ws is not None
    write_matrix(
        ws,
        [
            ["CustomerCode", "Name"],
            ["C-001", "Alpha"],
            ["C-002", "Beta"],
            ["C-003", "Gamma"],
            ["C-004", "Delta"],
        ],
    )
    bold_header(ws, 1, 2)
    for row in range(2, 6):
        ws.cell(row, 1).number_format = "@"
    return wb


def build_rel_duplicate_identifier(_seed: int) -> Workbook:
    wb = new_workbook(sheet_title="Dup")
    ws = wb.active
    assert ws is not None
    write_matrix(
        ws,
        [
            ["Code", "Label"],
            ["X", "one"],
            ["X", "two"],
            ["Y", "three"],
            ["Y", "four"],
        ],
    )
    bold_header(ws, 1, 2)
    return wb


def build_rel_composite_key(_seed: int) -> Workbook:
    wb = new_workbook(sheet_title="Lines")
    ws = wb.active
    assert ws is not None
    write_matrix(
        ws,
        [
            ["OrderId", "LineNo", "Qty"],
            ["O1", 1, 10],
            ["O1", 2, 5],
            ["O2", 1, 7],
            ["O2", 2, 3],
        ],
    )
    bold_header(ws, 1, 3)
    return wb


def build_rel_customers_orders(_seed: int) -> Workbook:
    wb = new_workbook(sheet_title="Customers")
    ws = wb.active
    assert ws is not None
    write_matrix(
        ws,
        [
            ["CustomerCode", "Name"],
            ["C-001", "Alpha"],
            ["C-002", "Beta"],
            ["C-003", "Gamma"],
        ],
    )
    bold_header(ws, 1, 2)
    for row in range(2, 5):
        ws.cell(row, 1).number_format = "@"

    orders = wb.create_sheet("Orders")
    write_matrix(
        orders,
        [
            ["OrderId", "CustomerCode", "Amount"],
            ["O-1", "C-001", 100],
            ["O-2", "C-001", 50],
            ["O-3", "C-002", 80],
            ["O-4", "C-003", 20],
        ],
    )
    orders["A1"].font = Font(bold=True)
    orders["B1"].font = Font(bold=True)
    orders["C1"].font = Font(bold=True)
    for row in range(2, 6):
        orders.cell(row, 2).number_format = "@"
    return wb


def build_rel_invoice_header_lines(_seed: int) -> Workbook:
    wb = new_workbook(sheet_title="Invoices")
    ws = wb.active
    assert ws is not None
    write_matrix(
        ws,
        [
            ["InvoiceId", "Customer"],
            ["INV-1", "A"],
            ["INV-2", "B"],
        ],
    )
    bold_header(ws, 1, 2)

    lines = wb.create_sheet("InvoiceLines")
    write_matrix(
        lines,
        [
            ["InvoiceId", "Line", "Product"],
            ["INV-1", 1, "P1"],
            ["INV-1", 2, "P2"],
            ["INV-2", 1, "P3"],
        ],
    )
    for cell in ("A1", "B1", "C1"):
        lines[cell].font = Font(bold=True)
    return wb


def build_rel_orphan_and_partial(_seed: int) -> Workbook:
    wb = new_workbook(sheet_title="Parents")
    ws = wb.active
    assert ws is not None
    write_matrix(
        ws,
        [
            ["Id", "Label"],
            ["P1", "one"],
            ["P2", "two"],
        ],
    )
    bold_header(ws, 1, 2)

    child = wb.create_sheet("Children")
    write_matrix(
        child,
        [
            ["ChildId", "ParentId"],
            ["C1", "P1"],
            ["C2", "P2"],
            ["C3", "P9"],  # orphan
            ["C4", None],  # nullable
        ],
    )
    for cell in ("A1", "B1"):
        child[cell].font = Font(bold=True)
    return wb


def build_rel_bridge_table(_seed: int) -> Workbook:
    wb = new_workbook(sheet_title="Students")
    ws = wb.active
    assert ws is not None
    write_matrix(
        ws,
        [
            ["StudentId", "Name"],
            ["S1", "Ann"],
            ["S2", "Bob"],
        ],
    )
    bold_header(ws, 1, 2)

    courses = wb.create_sheet("Courses")
    write_matrix(
        courses,
        [
            ["CourseId", "Title"],
            ["K1", "Math"],
            ["K2", "History"],
        ],
    )
    for cell in ("A1", "B1"):
        courses[cell].font = Font(bold=True)

    bridge = wb.create_sheet("Enrollment")
    write_matrix(
        bridge,
        [
            ["StudentId", "CourseId"],
            ["S1", "K1"],
            ["S1", "K2"],
            ["S2", "K1"],
        ],
    )
    for cell in ("A1", "B1"):
        bridge[cell].font = Font(bold=True)
    return wb


RELATIONSHIP_SPECS: list[ScenarioSpec] = [
    ScenarioSpec(
        scenario_id="rel_simple_primary_key",
        category="relationships",
        description="Unique non-null code as PK candidate",
        relative_workbook="workbooks/relationships/rel_simple_primary_key.xlsx",
        generator_name="relationship_scenarios.build_rel_simple_primary_key",
        intentions=["Detect primary key candidate"],
        features=["relationships", "primary_key"],
        expected_skeleton={
            "inspection": {"workbook": {"worksheet_count": 1}},
            "relationships": {
                "sheets": [
                    {
                        "name": "Customers",
                        "primary_keys": [
                            {
                                "column_index": 1,
                                "minimum_confidence": 0.55,
                            }
                        ],
                    }
                ]
            }
        },
    ),
    ScenarioSpec(
        scenario_id="rel_duplicate_identifier",
        category="relationships",
        description="Duplicated codes should not be strong PK",
        relative_workbook="workbooks/relationships/rel_duplicate_identifier.xlsx",
        generator_name="relationship_scenarios.build_rel_duplicate_identifier",
        intentions=["Reject duplicate identifier as PK"],
        features=["relationships", "false_pk"],
        expected_skeleton={
            "inspection": {"workbook": {"worksheet_count": 1}},
            "relationships": {
                "sheets": [
                    {
                        "name": "Dup",
                        "primary_keys": [
                            {
                                "column_index": 1,
                                "maximum_confidence": 0.7,
                            }
                        ],
                    }
                ]
            }
        },
    ),
    ScenarioSpec(
        scenario_id="rel_composite_key",
        category="relationships",
        description="OrderId+LineNo composite uniqueness",
        relative_workbook="workbooks/relationships/rel_composite_key.xlsx",
        generator_name="relationship_scenarios.build_rel_composite_key",
        intentions=["Detect composite key"],
        features=["relationships", "composite_key"],
        expected_skeleton={
            "inspection": {"workbook": {"worksheet_count": 1}},
            "relationships": {
                "sheets": [
                    {
                        "name": "Lines",
                        "composite_keys_min": 1,
                    }
                ]
            }
        },
    ),
    ScenarioSpec(
        scenario_id="rel_customers_orders",
        category="relationships",
        description="Orders.CustomerCode references Customers.CustomerCode",
        relative_workbook="workbooks/relationships/rel_customers_orders.xlsx",
        generator_name="relationship_scenarios.build_rel_customers_orders",
        intentions=["Detect FK inclusion"],
        features=["relationships", "foreign_key"],
        expected_skeleton={
            "inspection": {"workbook": {"worksheet_count": 2}},
            "relationships": {
                "foreign_keys": [
                    {
                        "from_sheet": "Orders",
                        "from_column_index": 2,
                        "to_sheet": "Customers",
                        "to_column_index": 1,
                        "minimum_inclusion": 0.99,
                        "minimum_confidence": 0.5,
                    }
                ]
            }
        },
    ),
    ScenarioSpec(
        scenario_id="rel_invoice_header_lines",
        category="relationships",
        description="Invoice header to lines 1:N",
        relative_workbook="workbooks/relationships/rel_invoice_header_lines.xlsx",
        generator_name="relationship_scenarios.build_rel_invoice_header_lines",
        intentions=["1:N cardinality"],
        features=["relationships", "one_to_many"],
        expected_skeleton={
            "inspection": {"workbook": {"worksheet_count": 2}},
            "relationships": {
                "foreign_keys": [
                    {
                        "from_sheet": "InvoiceLines",
                        "from_column_index": 1,
                        "to_sheet": "Invoices",
                        "to_column_index": 1,
                        "cardinality": "one_to_many",
                    }
                ]
            }
        },
    ),
    ScenarioSpec(
        scenario_id="rel_orphan_and_partial",
        category="relationships",
        description="Orphan and nullable FK values",
        relative_workbook="workbooks/relationships/rel_orphan_and_partial.xlsx",
        generator_name="relationship_scenarios.build_rel_orphan_and_partial",
        intentions=["Surface orphans and uncertainty"],
        features=["relationships", "orphans"],
        expected_skeleton={
            "inspection": {"workbook": {"worksheet_count": 2}},
            "relationships": {
                "foreign_keys": [
                    {
                        "from_sheet": "Children",
                        "from_column_index": 2,
                        "to_sheet": "Parents",
                        "to_column_index": 1,
                        "has_orphans": True,
                    }
                ]
            }
        },
    ),
    ScenarioSpec(
        scenario_id="rel_bridge_table",
        category="relationships",
        description="Enrollment bridge between students and courses",
        relative_workbook="workbooks/relationships/rel_bridge_table.xlsx",
        generator_name="relationship_scenarios.build_rel_bridge_table",
        intentions=["Structural N:M / bridge"],
        features=["relationships", "many_to_many"],
        expected_skeleton={
            "inspection": {"workbook": {"worksheet_count": 3}},
            "relationships": {
                "foreign_keys_min": 1,
            }
        },
    ),
]

BUILDERS = {
    "relationship_scenarios.build_rel_simple_primary_key": build_rel_simple_primary_key,
    "relationship_scenarios.build_rel_duplicate_identifier": build_rel_duplicate_identifier,
    "relationship_scenarios.build_rel_composite_key": build_rel_composite_key,
    "relationship_scenarios.build_rel_customers_orders": build_rel_customers_orders,
    "relationship_scenarios.build_rel_invoice_header_lines": build_rel_invoice_header_lines,
    "relationship_scenarios.build_rel_orphan_and_partial": build_rel_orphan_and_partial,
    "relationship_scenarios.build_rel_bridge_table": build_rel_bridge_table,
}
