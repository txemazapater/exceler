from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from tests.generators.catalog import ALL_SPECS, get_builder
from tests.generators.workbook_factory import (
    ScenarioSpec,
    save_workbook,
    workbook_path,
    write_expected_skeleton,
    write_index,
    write_manifest,
)


def generate_all(
    *,
    specs: list[ScenarioSpec] | None = None,
    root: Path | None = None,
) -> list[Path]:
    """Generate fixtures, manifests and expected skeletons for the given catalog."""
    active_specs = list(ALL_SPECS if specs is None else specs)
    written: list[Path] = []
    for spec in active_specs:
        builder = get_builder(spec.generator_name)
        if spec.seed is None:
            raise ValueError(f"{spec.scenario_id}: cannot generate without a seed")
        wb = builder(spec.seed)
        path = workbook_path(spec, root=root)
        save_workbook(wb, path)
        write_manifest(spec, root=root)
        write_expected_skeleton(spec, root=root)
        # Round-trip open validates the file is readable without macros/network.
        load_workbook(path, read_only=True, data_only=False)
        written.append(path)
    written.append(write_index(active_specs, root=root))
    return written


def main() -> None:
    paths = generate_all()
    print(f"Generated {len(ALL_SPECS)} scenarios ({len(paths)} artifacts).")


if __name__ == "__main__":
    main()
