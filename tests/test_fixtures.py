from __future__ import annotations

import json
from pathlib import Path

import pytest
from openpyxl import load_workbook
from tests.generators.catalog import ALL_SPECS
from tests.generators.generate_fixtures import generate_all
from tests.generators.verify_fixtures import verify_all
from tests.generators.workbook_factory import fixtures_root, manifest_path, workbook_path

pytestmark = pytest.mark.unit


def test_catalog_has_minimum_coverage() -> None:
    assert len(ALL_SPECS) >= 10
    scenario_ids = {spec.scenario_id for spec in ALL_SPECS}
    assert "hell_erp_clientes" in scenario_ids
    assert "hell_erp_facturas" in scenario_ids
    assert "simple_rectangular_table" in scenario_ids
    assert "xlsm_container" in scenario_ids


def test_generate_and_verify_roundtrip() -> None:
    generate_all()
    errors = verify_all()
    assert errors == []


def test_manifests_match_workbooks() -> None:
    generate_all()
    for spec in ALL_SPECS:
        man = json.loads(manifest_path(spec).read_text(encoding="utf-8"))
        wb = workbook_path(spec)
        assert wb.exists()
        assert man["workbook"].endswith(wb.name)
        assert man["seed"] == spec.seed
        loaded = load_workbook(wb, read_only=True, data_only=False)
        assert loaded.sheetnames
        loaded.close()


def test_fixtures_stay_under_fixtures_root() -> None:
    root = fixtures_root().resolve()
    for spec in ALL_SPECS:
        path = workbook_path(spec).resolve()
        assert root in path.parents or path == root
        assert ".." not in Path(spec.relative_workbook).parts
