from __future__ import annotations

from collections.abc import Callable

from openpyxl import Workbook
from tests.generators import corporate_scenarios, structural_scenarios
from tests.generators.workbook_factory import ScenarioSpec

Builder = Callable[[int], Workbook]

ALL_SPECS: list[ScenarioSpec] = [
    *structural_scenarios.MINIMAL_SPECS,
    *corporate_scenarios.CORPORATE_SPECS,
]

ALL_BUILDERS: dict[str, Builder] = {}
for name, fn in structural_scenarios.BUILDERS.items():
    ALL_BUILDERS[name] = fn  # type: ignore[assignment]
for name, fn in corporate_scenarios.BUILDERS.items():
    ALL_BUILDERS[name] = fn  # type: ignore[assignment]


def get_builder(name: str) -> Builder:
    try:
        return ALL_BUILDERS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown generator: {name}") from exc


def specs_by_id() -> dict[str, ScenarioSpec]:
    return {spec.scenario_id: spec for spec in ALL_SPECS}
