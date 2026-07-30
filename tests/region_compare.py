"""Partial expectation comparator for Phase 2B region contracts."""

from __future__ import annotations

from typing import Any

from tests.inspection_compare import ExpectationMismatchError

from exceler.domain.regions.models import LogicalRegion, RegionDetectionResult, SheetRegions


def _find_sheet(result: RegionDetectionResult, name: str | None) -> SheetRegions | None:
    if name is None and result.sheets:
        return result.sheets[0]
    for sheet in result.sheets:
        if sheet.sheet_name == name:
            return sheet
    return None


def _bbox_match(region: LogicalRegion, expected: dict[str, Any]) -> bool:
    box = region.bounding_box
    return (
        box.first_row == expected.get("first_row", box.first_row)
        and box.last_row == expected.get("last_row", box.last_row)
        and box.first_col == expected.get("first_col", box.first_col)
        and box.last_col == expected.get("last_col", box.last_col)
    )


def _find_region(
    regions: tuple[LogicalRegion, ...],
    expected: dict[str, Any],
) -> LogicalRegion | None:
    candidates = list(regions)
    if "region_type" in expected:
        candidates = [r for r in candidates if r.region_type.value == expected["region_type"]]
    if "bbox" in expected:
        bbox = expected["bbox"]
        candidates = [r for r in candidates if _bbox_match(r, bbox)]
    if not candidates:
        return None
    return candidates[0]


def compare_region_expectations(
    *,
    scenario_id: str,
    result: RegionDetectionResult,
    expected: dict[str, Any],
) -> None:
    """Compare partial expectations.regions against a detection result."""
    if not expected:
        return

    for idx, sheet_exp in enumerate(expected.get("sheets") or []):
        sheet = _find_sheet(result, sheet_exp.get("name"))
        path = f"expectations.regions.sheets[{idx}]"
        if sheet is None:
            raise ExpectationMismatchError(scenario_id, path, sheet_exp, None)

        if "name" in sheet_exp and sheet.sheet_name != sheet_exp["name"]:
            raise ExpectationMismatchError(
                scenario_id, f"{path}.name", sheet_exp["name"], sheet.sheet_name
            )

        n = len(sheet.regions)
        if "region_count" in sheet_exp and n != sheet_exp["region_count"]:
            raise ExpectationMismatchError(
                scenario_id, f"{path}.region_count", sheet_exp["region_count"], n
            )
        if "region_count_min" in sheet_exp and n < sheet_exp["region_count_min"]:
            raise ExpectationMismatchError(
                scenario_id,
                f"{path}.region_count_min",
                f">={sheet_exp['region_count_min']}",
                n,
            )
        if "region_count_max" in sheet_exp and n > sheet_exp["region_count_max"]:
            raise ExpectationMismatchError(
                scenario_id,
                f"{path}.region_count_max",
                f"<={sheet_exp['region_count_max']}",
                n,
            )

        actual_types = {r.region_type.value for r in sheet.regions}
        for needed in sheet_exp.get("contains_types") or []:
            if needed not in actual_types:
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{path}.contains_types",
                    needed,
                    sorted(actual_types),
                )

        if sheet_exp.get("has_parent_child"):
            linked = any(r.parent_id for r in sheet.regions) or any(
                r.children_ids for r in sheet.regions
            )
            if not linked:
                raise ExpectationMismatchError(scenario_id, f"{path}.has_parent_child", True, False)

        for r_idx, region_exp in enumerate(sheet_exp.get("regions") or []):
            region = _find_region(sheet.regions, region_exp)
            rpath = f"{path}.regions[{r_idx}]"
            if region is None:
                raise ExpectationMismatchError(scenario_id, rpath, region_exp, None)
            if (
                "region_type" in region_exp
                and region.region_type.value != region_exp["region_type"]
            ):
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{rpath}.region_type",
                    region_exp["region_type"],
                    region.region_type.value,
                )
            if "bbox" in region_exp and not _bbox_match(region, region_exp["bbox"]):
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{rpath}.bbox",
                    region_exp["bbox"],
                    region.bounding_box.to_dict(),
                )
            if region_exp.get("has_footer") and not region.footer_row_indices:
                raise ExpectationMismatchError(scenario_id, f"{rpath}.has_footer", True, False)
            if region_exp.get("has_header") and not region.header_row_indices:
                raise ExpectationMismatchError(scenario_id, f"{rpath}.has_header", True, False)
            if "parent_of_type" in region_exp:
                child_types = {
                    child.region_type.value
                    for child in sheet.regions
                    if child.id in region.children_ids
                }
                if region_exp["parent_of_type"] not in child_types:
                    raise ExpectationMismatchError(
                        scenario_id,
                        f"{rpath}.parent_of_type",
                        region_exp["parent_of_type"],
                        sorted(child_types),
                    )
