from __future__ import annotations

from pathlib import Path

import pytest
from tests.generators.catalog import ALL_SPECS
from tests.generators.workbook_factory import workbook_path
from tests.inspection_compare import compare_inspection_expectations

from exceler.application.workbook.serialization import deterministic_inspection_dict
from exceler.domain.workbook.errors import (
    InvalidWorkbookError,
    UnsupportedWorkbookFormatError,
    WorkbookLimitExceededError,
    WorkbookNotFoundError,
)
from exceler.domain.workbook.models import WorkbookInspectionOptions
from exceler.infrastructure.workbook.local_source import LocalWorkbookSource
from exceler.infrastructure.workbook.openpyxl_reader import OpenPyxlWorkbookReader

pytestmark = pytest.mark.unit

READER = OpenPyxlWorkbookReader()


def _inspect(path: Path, **kwargs: object):
    options = WorkbookInspectionOptions(**kwargs) if kwargs else WorkbookInspectionOptions()
    return READER.inspect(LocalWorkbookSource(path), options)


def test_contract_inspection_against_expected() -> None:
    for spec in ALL_SPECS:
        expected = spec.expected_skeleton.get("inspection")
        if not expected:
            continue
        path = workbook_path(spec)
        assert path.exists(), f"missing workbook for {spec.scenario_id}"
        inspection = _inspect(path)
        compare_inspection_expectations(
            scenario_id=spec.scenario_id,
            inspection=inspection,
            expected=expected,
        )


@pytest.mark.parametrize(
    "scenario_id",
    [
        "simple_rectangular_table",
        "hidden_sheet",
        "formulas",
        "excel_structured_table",
        "xlsm_container",
        "xlsm_with_vba_stub",
        "inflated_dimension",
        "cell_physical_types",
    ],
)
def test_key_scenarios_present(scenario_id: str) -> None:
    ids = {spec.scenario_id for spec in ALL_SPECS}
    assert scenario_id in ids


def test_inspection_is_deterministic() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "formulas"))
    a = deterministic_inspection_dict(_inspect(path))
    b = deterministic_inspection_dict(_inspect(path))
    assert a == b


def test_inspection_does_not_mutate_source(tmp_path: Path) -> None:
    # Copy a versioned fixture into tmp and inspect there.
    src = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "simple_rectangular_table"))
    target = tmp_path / src.name
    data = src.read_bytes()
    target.write_bytes(data)
    before_stat = target.stat()
    before_hash = LocalWorkbookSource(target).content_hash()
    _inspect(target)
    after_stat = target.stat()
    after_hash = LocalWorkbookSource(target).content_hash()
    assert after_hash == before_hash
    assert after_stat.st_size == before_stat.st_size
    assert after_stat.st_mtime_ns == before_stat.st_mtime_ns
    assert list(tmp_path.iterdir()) == [target]


def test_missing_file() -> None:
    with pytest.raises(WorkbookNotFoundError):
        _inspect(Path("definitely-missing-exceler.xlsx"))


def test_unsupported_extension(tmp_path: Path) -> None:
    path = tmp_path / "notes.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(UnsupportedWorkbookFormatError):
        _inspect(path)


def test_corrupt_zip(tmp_path: Path) -> None:
    path = tmp_path / "bad.xlsx"
    path.write_bytes(b"PK\x03\x04not-a-workbook")
    with pytest.raises(InvalidWorkbookError):
        _inspect(path)


def test_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.xlsx"
    path.write_bytes(b"")
    with pytest.raises(InvalidWorkbookError):
        _inspect(path)


def test_directory_path(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedWorkbookFormatError):
        _inspect(tmp_path)


def test_max_file_size_limit(tmp_path: Path) -> None:
    src = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "empty_sheet"))
    target = tmp_path / "tiny.xlsx"
    target.write_bytes(src.read_bytes())
    with pytest.raises(WorkbookLimitExceededError):
        _inspect(target, max_file_size_bytes=10)


def test_formulas_not_evaluated() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "formulas"))
    inspection = _inspect(path)
    cell = next(c for c in inspection.worksheets[0].cells if c.coordinate == "C2")
    assert cell.formula == "=A2*B2"
    assert cell.value.kind.value == "null"


def test_xlsm_without_vba() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "xlsm_container"))
    inspection = _inspect(path)
    assert inspection.format.value == "xlsm"
    assert inspection.has_vba_project is False


def test_xlsm_with_vba_stub_detected() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "xlsm_with_vba_stub"))
    assert path.exists()
    inspection = _inspect(path)
    assert inspection.has_vba_project is True
    assert any(w.code.value == "VBA_PROJECT_PRESENT" for w in inspection.warnings)


def test_serialization_schema_version() -> None:
    from exceler.application.workbook.serialization import inspection_to_dict

    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "hidden_sheet"))
    payload = inspection_to_dict(_inspect(path))
    assert payload["schema_version"] == 1
    assert payload["inspection"]["worksheets"][1]["visibility"] == "hidden"
