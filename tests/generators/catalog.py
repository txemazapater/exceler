from __future__ import annotations

from collections.abc import Callable

from openpyxl import Workbook
from tests.generators import (
    corporate_scenarios,
    inspection_scenarios,
    profiling_scenarios,
    region_scenarios,
    relationship_scenarios,
    structural_scenarios,
)
from tests.generators.workbook_factory import ScenarioSpec

Builder = Callable[[int], Workbook]
SpecialSaver = Callable[[Workbook, object], None]

ALL_SPECS: list[ScenarioSpec] = [
    *structural_scenarios.MINIMAL_SPECS,
    *region_scenarios.REGION_SPECS,
    *inspection_scenarios.INSPECTION_SPECS,
    *profiling_scenarios.PROFILE_SPECS,
    *relationship_scenarios.RELATIONSHIP_SPECS,
    *corporate_scenarios.CORPORATE_SPECS,
]

ALL_BUILDERS: dict[str, Builder] = {}
for name, fn in structural_scenarios.BUILDERS.items():
    ALL_BUILDERS[name] = fn  # type: ignore[assignment]
for name, fn in region_scenarios.BUILDERS.items():
    ALL_BUILDERS[name] = fn  # type: ignore[assignment]
for name, fn in inspection_scenarios.BUILDERS.items():
    ALL_BUILDERS[name] = fn  # type: ignore[assignment]
for name, fn in profiling_scenarios.BUILDERS.items():
    ALL_BUILDERS[name] = fn  # type: ignore[assignment]
for name, fn in relationship_scenarios.BUILDERS.items():
    ALL_BUILDERS[name] = fn
for name, fn in corporate_scenarios.BUILDERS.items():
    ALL_BUILDERS[name] = fn  # type: ignore[assignment]

SPECIAL_SAVERS: dict[str, SpecialSaver] = {}
for name, fn in getattr(inspection_scenarios, "SPECIAL_SAVERS", {}).items():
    SPECIAL_SAVERS[name] = fn


def get_builder(name: str) -> Builder:
    try:
        return ALL_BUILDERS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown generator: {name}") from exc


def get_special_saver(name: str) -> SpecialSaver | None:
    return SPECIAL_SAVERS.get(name)


def specs_by_id() -> dict[str, ScenarioSpec]:
    return {spec.scenario_id: spec for spec in ALL_SPECS}
