"""Phase 2C profiling contract and unit tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from tests.generators.catalog import ALL_SPECS
from tests.generators.workbook_factory import workbook_path
from tests.profiling_compare import compare_profiling_expectations

from exceler.application.profiling.normalization import looks_uuid
from exceler.application.profiling.profiler import DeterministicRegionProfiler
from exceler.application.profiling.serialization import profile_to_dict
from exceler.application.regions.heuristic_detector import HeuristicRegionDetector
from exceler.domain.profiling.errors import ProfilingInputMismatchError
from exceler.domain.profiling.options import PROFILING_SCHEMA_VERSION, ProfilingOptions
from exceler.domain.regions.models import RegionDetectionResult
from exceler.domain.workbook.models import WorkbookInspectionOptions
from exceler.infrastructure.workbook.local_source import LocalWorkbookSource
from exceler.infrastructure.workbook.openpyxl_reader import OpenPyxlWorkbookReader

pytestmark = pytest.mark.unit

READER = OpenPyxlWorkbookReader()
DETECTOR = HeuristicRegionDetector()
PROFILER = DeterministicRegionProfiler()

PROFILE_SCENARIO_IDS = {
    "profile_core_types",
    "profile_logical_specials",
    "profile_mixed_and_anomalies",
    "profile_id_and_category",
    "profile_headers",
}


def _run(path: Path, **profile_kwargs: object):
    inspection = READER.inspect(LocalWorkbookSource(path), WorkbookInspectionOptions())
    regions = DETECTOR.detect(inspection)
    options = ProfilingOptions(**profile_kwargs) if profile_kwargs else ProfilingOptions()
    return inspection, regions, PROFILER.profile(inspection, regions, options)


def test_contract_profiling_against_expected() -> None:
    for spec in ALL_SPECS:
        expected = spec.expected_skeleton.get("profiling")
        if not expected:
            continue
        path = workbook_path(spec)
        assert path.exists(), f"missing workbook for {spec.scenario_id}"
        _inspection, _regions, result = _run(path)
        compare_profiling_expectations(
            scenario_id=spec.scenario_id,
            result=result,
            expected=expected,
        )


@pytest.mark.parametrize("scenario_id", sorted(PROFILE_SCENARIO_IDS))
def test_profile_scenarios_registered(scenario_id: str) -> None:
    assert scenario_id in {spec.scenario_id for spec in ALL_SPECS}


def test_profiler_modules_never_import_openpyxl() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "exceler" / "application" / "profiling"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] != "openpyxl" for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] != "openpyxl"


def test_profiling_is_deterministic() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "profile_core_types"))
    _i, _r, a = _run(path)
    _i2, _r2, b = _run(path)
    assert profile_to_dict(a) == profile_to_dict(b)
    assert a.profiling_schema_version == PROFILING_SCHEMA_VERSION


def test_hash_mismatch_raises() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "profile_core_types"))
    inspection, regions, _ = _run(path)
    bad = RegionDetectionResult(
        workbook_hash="0" * 64,
        inspector_version=regions.inspector_version,
        detector_version=regions.detector_version,
        regions_schema_version=regions.regions_schema_version,
        sheets=regions.sheets,
        warnings=regions.warnings,
        limitations=regions.limitations,
    )
    with pytest.raises(ProfilingInputMismatchError):
        PROFILER.profile(inspection, bad)


def test_blank_vs_null_separation() -> None:
    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "profile_mixed_and_anomalies")
    )
    _i, _r, result = _run(path)
    region = result.sheets[0].region_profiles[0]
    blankish = next(c for c in region.columns if c.column_index == 3)
    assert blankish.statistics.whitespace_only_count >= 1
    assert blankish.statistics.blank_string_count + blankish.statistics.null_count >= 1


def test_leading_zeroes_not_integer() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "profile_core_types"))
    _i, _r, result = _run(path)
    col = result.sheets[0].region_profiles[0].columns[0]
    selected = col.logical_type_inference.selected_type.value
    alts = {a.type.value for a in col.logical_type_inference.alternatives}
    assert selected in {"code", "identifier", "text"} or "code" in alts
    assert selected != "integer"


def test_uuid_helper() -> None:
    assert looks_uuid("550e8400-e29b-41d4-a716-446655440000")
    assert not looks_uuid("not-a-uuid")


def test_formula_counted_without_evaluation() -> None:
    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "profile_mixed_and_anomalies")
    )
    _i, _r, result = _run(path)
    formula_col = next(
        c for c in result.sheets[0].region_profiles[0].columns if c.column_index == 5
    )
    assert formula_col.statistics.formula_count >= 1


def test_cli_workbook_profile_json(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from exceler.cli.main import app

    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "profile_core_types"))
    out = tmp_path / "profile.json"
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["workbook", "profile", str(path), "--format", "json", "--pretty", "--output", str(out)],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["profiling_schema_version"] == PROFILING_SCHEMA_VERSION
    assert payload["sheets"]


def test_header_excluded_from_statistics() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "profile_core_types"))
    _i, _r, result = _run(path)
    col = result.sheets[0].region_profiles[0].columns[0]
    assert "Code" in col.header_values
    assert all(sample.original != "Code" for sample in col.sample)


def test_footer_excluded_from_data_profile() -> None:
    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "profile_mixed_and_anomalies")
    )
    _i, regions, result = _run(path)
    region = regions.sheets[0].regions[0]
    assert 5 in region.footer_row_indices
    date_col = result.sheets[0].region_profiles[0].columns[0]
    assert all(sample.original != "TOTAL" for sample in date_col.sample)


def test_partial_inspection_marks_partial_status() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "profile_core_types"))
    inspection = READER.inspect(
        LocalWorkbookSource(path),
        WorkbookInspectionOptions(max_cells_observed=12),
    )
    assert inspection.completion_status.value == "partial"
    regions = DETECTOR.detect(inspection)
    result = PROFILER.profile(inspection, regions)
    assert any("partial" in w.lower() for w in result.warnings)
    statuses = {rp.profiling_status.value for s in result.sheets for rp in s.region_profiles}
    assert statuses
    assert "partial" in statuses or "insufficient_data" in statuses


def test_distinct_limit_marks_truncated() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "profile_id_and_category"))
    _i, _r, result = _run(path, max_distinct_values_tracked=2)
    free = next(c for c in result.sheets[0].region_profiles[0].columns if c.column_index == 5)
    assert free.statistics.exactness.value in {"truncated", "estimated"}


def test_percentage_and_currency_inference() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "profile_logical_specials"))
    _i, _r, result = _run(path)
    cols = result.sheets[0].region_profiles[0].columns
    assert cols[0].logical_type_inference.selected_type.value == "percentage"
    money = cols[1].logical_type_inference.selected_type.value
    assert money in {"currency", "decimal", "number"}
