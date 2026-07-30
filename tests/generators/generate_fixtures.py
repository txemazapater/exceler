from __future__ import annotations

import json
from pathlib import Path

from openpyxl import load_workbook
from tests.generators.catalog import ALL_SPECS, get_builder
from tests.generators.workbook_factory import (
    fixtures_root,
    save_workbook,
    workbook_path,
    write_expected_skeleton,
    write_manifest,
)


def generate_all(*, root: Path | None = None) -> list[Path]:
    """Generate all versioned fixtures, manifests and expected skeletons."""
    _ = root  # reserved for future alternate roots; always use FIXTURES_ROOT
    written: list[Path] = []
    for spec in ALL_SPECS:
        builder = get_builder(spec.generator_name)
        wb = builder(spec.seed)
        path = workbook_path(spec)
        # Ensure xlsm extension is preserved.
        save_workbook(wb, path)
        write_manifest(spec)
        write_expected_skeleton(spec)
        # Round-trip open validates the file is readable without macros/network.
        load_workbook(path, read_only=True, data_only=False)
        written.append(path)
    index = {
        "scenarios": [spec.scenario_id for spec in ALL_SPECS],
        "count": len(ALL_SPECS),
    }
    index_path = fixtures_root() / "index.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    written.append(index_path)
    return written


def main() -> None:
    paths = generate_all()
    print(f"Generated {len(ALL_SPECS)} scenarios ({len(paths)} artifacts).")


if __name__ == "__main__":
    main()
