"""Phase 2B region detection contract and unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.generators.catalog import ALL_SPECS
from tests.generators.workbook_factory import workbook_path
from tests.region_compare import compare_region_expectations

from exceler.application.regions.heuristic_detector import HeuristicRegionDetector
from exceler.application.regions.serialization import regions_to_dict
from exceler.domain.regions.models import RegionType
from exceler.domain.regions.options import REGIONS_SCHEMA_VERSION
from exceler.domain.workbook.models import WorkbookInspectionOptions
from exceler.infrastructure.workbook.local_source import LocalWorkbookSource
from exceler.infrastructure.workbook.openpyxl_reader import OpenPyxlWorkbookReader

pytestmark = pytest.mark.unit

READER = OpenPyxlWorkbookReader()
DETECTOR = HeuristicRegionDetector()

REGION_SCENARIO_IDS = {
    "two_regions_one_sheet",
    "title_above_header",
    "table_with_totals_footer",
    "note_block_below_table",
    "nested_title_and_table",
    "false_gap_inside_table",
    "styled_separator_blocks",
    "structured_table_partial_overlap",
}


def test_contract_regions_against_expected() -> None:
    for spec in ALL_SPECS:
        expected = spec.expected_skeleton.get("regions")
        if not expected:
            continue
        path = workbook_path(spec)
        assert path.exists(), f"missing workbook for {spec.scenario_id}"
        inspection = READER.inspect(LocalWorkbookSource(path), WorkbookInspectionOptions())
        result = DETECTOR.detect(inspection)
        compare_region_expectations(
            scenario_id=spec.scenario_id,
            result=result,
            expected=expected,
        )


@pytest.mark.parametrize("scenario_id", sorted(REGION_SCENARIO_IDS))
def test_region_scenarios_registered(scenario_id: str) -> None:
    ids = {spec.scenario_id for spec in ALL_SPECS}
    assert scenario_id in ids


def test_detector_never_imports_openpyxl() -> None:
    import ast
    from pathlib import Path

    import exceler.application.regions.heuristic_detector as mod

    tree = ast.parse(Path(mod.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] != "openpyxl" for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] != "openpyxl"


def test_region_detection_is_deterministic() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "two_regions_one_sheet"))
    inspection = READER.inspect(LocalWorkbookSource(path))
    a = regions_to_dict(DETECTOR.detect(inspection))
    b = regions_to_dict(DETECTOR.detect(inspection))
    assert a == b
    assert a["regions_schema_version"] == REGIONS_SCHEMA_VERSION


def test_structured_table_seeding() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "excel_structured_table"))
    inspection = READER.inspect(LocalWorkbookSource(path))
    result = DETECTOR.detect(inspection)
    sheet = result.sheets[0]
    seeded = [r for r in sheet.regions if r.id.startswith(f"{sheet.sheet_name}::structured::")]
    assert seeded
    assert all(r.region_type is RegionType.TABLE and r.confidence == 1.0 for r in seeded)
    # Pure structured sheet should not keep a duplicate heuristic covering the same bbox.
    structured_boxes = {
        (
            r.bounding_box.first_row,
            r.bounding_box.last_row,
            r.bounding_box.first_col,
            r.bounding_box.last_col,
        )
        for r in seeded
    }
    heuristic = [r for r in sheet.regions if "::structured::" not in r.id]
    for region in heuristic:
        key = (
            region.bounding_box.first_row,
            region.bounding_box.last_row,
            region.bounding_box.first_col,
            region.bounding_box.last_col,
        )
        assert key not in structured_boxes


def test_structured_table_partial_overlap_splits() -> None:
    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "structured_table_partial_overlap")
    )
    inspection = READER.inspect(LocalWorkbookSource(path))
    result = DETECTOR.detect(inspection)
    sheet = result.sheets[0]
    seeded = [r for r in sheet.regions if "::structured::" in r.id]
    heuristic = [r for r in sheet.regions if "::structured::" not in r.id]
    assert len(seeded) == 1
    assert seeded[0].bounding_box.to_dict() == {
        "first_row": 1,
        "last_row": 4,
        "first_col": 1,
        "last_col": 2,
    }
    assert heuristic
    assert all(r.bounding_box.first_col >= 3 for r in heuristic)


def test_occupancy_layers_are_distinct() -> None:
    from exceler.application.regions.heuristic_detector import _build_occupancy

    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "false_gap_inside_table"))
    inspection = READER.inspect(LocalWorkbookSource(path))
    facts = _build_occupancy(inspection.worksheets[0])
    observed = {k for k, f in facts.items() if f.observed}
    content = {k for k, f in facts.items() if f.has_content}
    visual = {k for k, f in facts.items() if f.visual}
    assert content <= visual
    assert observed  # inspection recorded cells
    # Empty bordered gap row is visual (and observed as formatted) but not content.
    gap_keys = {(4, 1), (4, 2)}
    assert gap_keys <= visual
    assert gap_keys.isdisjoint(content)

    result = DETECTOR.detect(inspection)
    stats = result.sheets[0].regions[0].statistics
    assert stats.content_occupied_count == stats.occupied_count
    assert stats.visual_occupied_count >= stats.content_occupied_count
    assert stats.observed_count >= stats.content_occupied_count
    assert "visual_density" in stats.to_dict()


def test_false_gap_stays_one_table() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "false_gap_inside_table"))
    inspection = READER.inspect(LocalWorkbookSource(path))
    result = DETECTOR.detect(inspection)
    regions = result.sheets[0].regions
    assert len(regions) == 1
    assert regions[0].region_type is RegionType.TABLE
    assert regions[0].bounding_box.last_row == 6


def test_cli_workbook_regions_json(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from exceler.cli.main import app

    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "two_regions_one_sheet"))
    out = tmp_path / "regions.json"
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["workbook", "regions", str(path), "--format", "json", "--pretty", "--output", str(out)],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["regions_schema_version"] == REGIONS_SCHEMA_VERSION
    assert len(payload["sheets"][0]["regions"]) == 2
