from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from tests.generators.catalog import ALL_SPECS, get_builder, specs_by_id
from tests.generators.workbook_factory import (
    expected_path,
    fixtures_root,
    manifest_path,
    save_workbook,
    workbook_path,
)


def _logical_snapshot(path: Path) -> dict[str, Any]:
    wb = load_workbook(path, data_only=False)
    sheets: dict[str, Any] = {}
    for name in wb.sheetnames:
        ws = wb[name]
        values: list[list[Any]] = []
        for row in ws.iter_rows(values_only=True):
            values.append(list(row))
        sheets[name] = {
            "state": ws.sheet_state,
            "merged": [str(r) for r in ws.merged_cells.ranges],
            "tables": sorted(ws.tables.keys()),
            "values": values,
        }
    return {
        "sheets": sheets,
        "defined_names": sorted(wb.defined_names.keys()),
    }


def verify_all() -> list[str]:
    errors: list[str] = []
    root = fixtures_root()
    by_id = specs_by_id()
    if len(by_id) != len(ALL_SPECS):
        errors.append("Duplicate scenario_id values in catalog")

    seen_workbooks: set[str] = set()
    for spec in ALL_SPECS:
        if not spec.seed:
            errors.append(f"{spec.scenario_id}: seed is missing")
        wb_key = spec.relative_workbook.replace("\\", "/")
        if wb_key in seen_workbooks:
            errors.append(f"Duplicate workbook path: {wb_key}")
        seen_workbooks.add(wb_key)

        man = manifest_path(spec)
        exp = expected_path(spec)
        wb = workbook_path(spec)
        if not man.exists():
            errors.append(f"{spec.scenario_id}: missing manifest {man}")
            continue
        if not exp.exists():
            errors.append(f"{spec.scenario_id}: missing expected skeleton {exp}")
        if not wb.exists():
            errors.append(f"{spec.scenario_id}: missing workbook {wb}")
            continue

        try:
            payload = json.loads(man.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{spec.scenario_id}: invalid manifest JSON ({exc})")
            continue

        if payload.get("scenario_id") != spec.scenario_id:
            errors.append(f"{spec.scenario_id}: manifest scenario_id mismatch")
        if payload.get("seed") != spec.seed:
            errors.append(f"{spec.scenario_id}: manifest seed mismatch")
        if payload.get("generator") != spec.generator_name:
            errors.append(f"{spec.scenario_id}: manifest generator mismatch")
        if payload.get("workbook") != wb_key:
            errors.append(f"{spec.scenario_id}: manifest workbook path mismatch")

        try:
            wb.resolve().relative_to(root.resolve())
        except ValueError:
            errors.append(f"{spec.scenario_id}: workbook escapes fixtures root")

        try:
            load_workbook(wb, read_only=True, data_only=False)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{spec.scenario_id}: workbook is not readable ({exc})")
            continue

        if spec.versioned:
            builder = get_builder(spec.generator_name)
            regenerated = builder(spec.seed)
            tmp_path = root / ".tmp_regen" / wb.name
            try:
                save_workbook(regenerated, tmp_path)
                if _logical_snapshot(tmp_path) != _logical_snapshot(wb):
                    errors.append(
                        f"{spec.scenario_id}: regenerated logical content differs "
                        "from versioned workbook"
                    )
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
                tmp_dir = tmp_path.parent
                if tmp_dir.exists() and not any(tmp_dir.iterdir()):
                    tmp_dir.rmdir()

    workbooks_dir = root / "workbooks"
    if workbooks_dir.exists():
        expected_files = {workbook_path(spec).resolve() for spec in ALL_SPECS}
        for path in workbooks_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".xlsx", ".xlsm"}:
                if path.resolve() not in expected_files:
                    errors.append(f"Orphan workbook: {path.relative_to(root)}")

    manifests_dir = root / "manifests"
    if manifests_dir.exists():
        expected_manifests = {manifest_path(spec).resolve() for spec in ALL_SPECS}
        for path in manifests_dir.rglob("*.json"):
            if path.resolve() not in expected_manifests:
                errors.append(f"Orphan manifest: {path.relative_to(root)}")

    return errors


def main() -> None:
    errors = verify_all()
    if errors:
        print("Fixture verification FAILED:")
        for item in errors:
            print(f" - {item}")
        raise SystemExit(1)
    print(f"Fixture verification OK ({len(ALL_SPECS)} scenarios).")


if __name__ == "__main__":
    main()
