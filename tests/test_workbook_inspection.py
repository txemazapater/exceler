from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pytest
from tests.generators.catalog import ALL_SPECS
from tests.generators.workbook_factory import workbook_path
from tests.inspection_compare import compare_inspection_expectations

from exceler.application.workbook.serialization import (
    deterministic_inspection_dict,
    inspection_to_dict,
)
from exceler.domain.workbook.enums import InspectionCompletionStatus, InspectionTruncationCode
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


def _options_from_expected(expected: dict) -> WorkbookInspectionOptions:
    raw = expected.get("options") or {}
    base = WorkbookInspectionOptions()
    return WorkbookInspectionOptions(
        include_empty_formatted_cells=base.include_empty_formatted_cells,
        include_comments=base.include_comments,
        include_hyperlinks=base.include_hyperlinks,
        include_external_links=base.include_external_links,
        max_worksheets=raw.get("max_worksheets", base.max_worksheets),
        max_cells_observed=raw.get("max_cells_observed", base.max_cells_observed),
        max_cells_scanned=raw.get("max_cells_scanned", base.max_cells_scanned),
        max_file_size_bytes=raw.get("max_file_size_bytes", base.max_file_size_bytes),
    )


def test_contract_inspection_against_expected() -> None:
    for spec in ALL_SPECS:
        expected = spec.expected_skeleton.get("inspection")
        if not expected:
            continue
        path = workbook_path(spec)
        assert path.exists(), f"missing workbook for {spec.scenario_id}"
        options = _options_from_expected(expected)
        inspection = READER.inspect(LocalWorkbookSource(path), options)
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
        "pathological_inflated_dimension",
        "max_observed_cells_partial",
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
    src = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "simple_rectangular_table"))
    target = tmp_path / src.name
    data = src.read_bytes()
    target.write_bytes(data)
    before_stat = target.stat()
    before_hash = sha256(data).hexdigest()
    _inspect(target)
    after_stat = target.stat()
    after_hash = sha256(target.read_bytes()).hexdigest()
    assert after_hash == before_hash
    assert after_stat.st_size == before_stat.st_size
    assert after_stat.st_mtime_ns == before_stat.st_mtime_ns
    assert list(tmp_path.iterdir()) == [target]


def test_payload_hash_identity_without_content_hash_call() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "formulas"))
    payload = path.read_bytes()

    class CountingSource:
        def __init__(self) -> None:
            self.open_count = 0
            self.hash_count = 0

        @property
        def name(self) -> str:
            return path.name

        @property
        def suggested_extension(self) -> str:
            return path.suffix

        def open_binary(self) -> BinaryIO:
            self.open_count += 1
            return BytesIO(payload)

        def size_bytes(self) -> int:
            return len(payload)

        def content_hash(self) -> str:
            self.hash_count += 1
            return "should-not-be-used"

        def modified_at_iso(self) -> str | None:
            return None

        def source_path(self) -> str | None:
            return str(path)

    source = CountingSource()
    inspection = READER.inspect(source)
    assert source.hash_count == 0
    assert source.open_count == 1
    assert inspection.file.content_hash == sha256(payload).hexdigest()
    assert inspection.file.size_bytes == len(payload)
    assert inspection.completion_status is InspectionCompletionStatus.COMPLETE


def test_source_size_mismatch_warns_but_uses_payload() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "empty_sheet"))
    payload = path.read_bytes()

    class MismatchSource:
        @property
        def name(self) -> str:
            return path.name

        @property
        def suggested_extension(self) -> str:
            return ".xlsx"

        def open_binary(self) -> BinaryIO:
            return BytesIO(payload)

        def size_bytes(self) -> int:
            return len(payload) + 99

        def modified_at_iso(self) -> str | None:
            return None

        def source_path(self) -> str | None:
            return None

    inspection = READER.inspect(MismatchSource())
    assert inspection.file.size_bytes == len(payload)
    assert inspection.file.content_hash == sha256(payload).hexdigest()
    assert any(w.code.value == "SOURCE_SIZE_CHANGED" for w in inspection.warnings)


def test_pathological_dimension_is_partial_and_bounded() -> None:
    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "pathological_inflated_dimension")
    )
    inspection = _inspect(path)
    assert inspection.completion_status is InspectionCompletionStatus.PARTIAL
    assert any(
        t.code is InspectionTruncationCode.MAX_CELLS_SCANNED for t in inspection.truncation_reasons
    )
    assert inspection.cells_scanned <= WorkbookInspectionOptions().max_cells_scanned
    # Must not approach the declared 10M rectangle.
    assert inspection.cells_scanned < 10_000


def test_max_observed_cells_partial() -> None:
    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "max_observed_cells_partial")
    )
    inspection = _inspect(path, max_cells_observed=20)
    assert inspection.completion_status is InspectionCompletionStatus.PARTIAL
    assert any(
        t.code is InspectionTruncationCode.MAX_CELLS_OBSERVED for t in inspection.truncation_reasons
    )
    assert inspection.cells_observed == 20
    coords = [c.coordinate for c in inspection.worksheets[0].cells]
    assert coords == sorted(
        coords,
        key=lambda c: (int("".join(ch for ch in c if ch.isdigit())), c),
    )


def test_cells_scanned_never_exceeds_budget() -> None:
    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "max_observed_cells_partial")
    )
    budget = 25
    inspection = _inspect(path, max_cells_scanned=budget)
    assert inspection.cells_scanned <= budget
    assert inspection.completion_status is InspectionCompletionStatus.PARTIAL
    assert any(
        t.code is InspectionTruncationCode.MAX_CELLS_SCANNED for t in inspection.truncation_reasons
    )


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
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "hidden_sheet"))
    payload = inspection_to_dict(_inspect(path))
    assert payload["schema_version"] == 3
    assert payload["inspection"]["completion_status"] == "complete"
    assert payload["inspection"]["truncation_reasons"] == []
    assert "cells_scanned" in payload["inspection"]
    assert payload["inspection"]["worksheets"][1]["visibility"] == "hidden"
