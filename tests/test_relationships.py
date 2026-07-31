"""Phase 2D relationship contract and unit tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from tests.generators.catalog import ALL_SPECS
from tests.generators.workbook_factory import workbook_path
from tests.relationships_compare import compare_relationship_expectations

from exceler.application.profiling.profiler import DeterministicRegionProfiler
from exceler.application.regions.heuristic_detector import HeuristicRegionDetector
from exceler.application.relationships.analyzer import DeterministicRelationshipAnalyzer
from exceler.application.relationships.serialization import relationships_to_dict
from exceler.domain.profiling.models import ProfilingResult
from exceler.domain.relationships.errors import RelationshipInputMismatchError
from exceler.domain.relationships.options import RELATIONSHIP_SCHEMA_VERSION, RelationshipOptions
from exceler.domain.workbook.models import WorkbookInspectionOptions
from exceler.infrastructure.workbook.local_source import LocalWorkbookSource
from exceler.infrastructure.workbook.openpyxl_reader import OpenPyxlWorkbookReader

pytestmark = pytest.mark.unit

READER = OpenPyxlWorkbookReader()
DETECTOR = HeuristicRegionDetector()
PROFILER = DeterministicRegionProfiler()
ANALYZER = DeterministicRelationshipAnalyzer()

REL_SCENARIO_IDS = {
    "rel_simple_primary_key",
    "rel_duplicate_identifier",
    "rel_composite_key",
    "rel_customers_orders",
    "rel_invoice_header_lines",
    "rel_orphan_and_partial",
    "rel_bridge_table",
}


def _run(path: Path, **rel_kwargs: object):
    inspection = READER.inspect(LocalWorkbookSource(path), WorkbookInspectionOptions())
    regions = DETECTOR.detect(inspection)
    profiling = PROFILER.profile(inspection, regions)
    options = RelationshipOptions(**rel_kwargs) if rel_kwargs else RelationshipOptions()
    result = ANALYZER.analyze(inspection, regions, profiling, options)
    return inspection, regions, profiling, result


def test_contract_relationships_against_expected() -> None:
    for spec in ALL_SPECS:
        expected = spec.expected_skeleton.get("relationships")
        if not expected:
            continue
        path = workbook_path(spec)
        assert path.exists(), f"missing workbook for {spec.scenario_id}"
        _i, _r, _p, result = _run(path)
        compare_relationship_expectations(
            scenario_id=spec.scenario_id,
            result=result,
            expected=expected,
        )


@pytest.mark.parametrize("scenario_id", sorted(REL_SCENARIO_IDS))
def test_relationship_scenarios_registered(scenario_id: str) -> None:
    assert scenario_id in {spec.scenario_id for spec in ALL_SPECS}


def test_relationship_modules_never_import_openpyxl() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "exceler" / "application" / "relationships"
    domain = Path(__file__).resolve().parents[1] / "src" / "exceler" / "domain" / "relationships"
    for path in list(root.rglob("*.py")) + list(domain.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] != "openpyxl" for alias in node.names)
                assert all(alias.name.split(".")[0] != "pandas" for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] != "openpyxl"
                assert node.module.split(".")[0] != "pandas"


def test_relationships_deterministic() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_customers_orders"))
    _a = _run(path)[3]
    _b = _run(path)[3]
    assert relationships_to_dict(_a) == relationships_to_dict(_b)
    assert _a.relationship_schema_version == RELATIONSHIP_SCHEMA_VERSION


def test_hash_mismatch_raises() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_simple_primary_key"))
    inspection, regions, profiling, _ = _run(path)
    bad = ProfilingResult(
        workbook_hash="0" * 64,
        inspector_version=profiling.inspector_version,
        region_detector_version=profiling.region_detector_version,
        regions_schema_version=profiling.regions_schema_version,
        profiler_version=profiling.profiler_version,
        profiling_schema_version=profiling.profiling_schema_version,
        sheets=profiling.sheets,
        warnings=profiling.warnings,
        limitations=profiling.limitations,
    )
    with pytest.raises(RelationshipInputMismatchError):
        ANALYZER.analyze(inspection, regions, bad)


def test_customers_orders_fk_inclusion() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_customers_orders"))
    _i, _r, _p, result = _run(path)
    assert result.foreign_keys
    fk = next(
        item
        for item in result.foreign_keys
        if item.from_column.sheet_name == "Orders" and item.to_column.sheet_name == "Customers"
    )
    assert fk.inclusion_ratio >= 0.99
    assert fk.orphan_count == 0


def test_composite_key_detected() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_composite_key"))
    _i, _r, _p, result = _run(path)
    assert any(sheet.composite_keys for sheet in result.sheets)


def test_cli_workbook_relationships_json(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from exceler.cli.main import app

    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_simple_primary_key"))
    out = tmp_path / "relationships.json"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "workbook",
            "relationships",
            str(path),
            "--format",
            "json",
            "--pretty",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["relationship_schema_version"] == RELATIONSHIP_SCHEMA_VERSION
    assert payload["sheets"]
