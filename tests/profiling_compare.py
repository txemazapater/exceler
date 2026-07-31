"""Partial expectation comparator for Phase 2C profiling contracts."""

from __future__ import annotations

from typing import Any

from tests.inspection_compare import ExpectationMismatchError

from exceler.domain.profiling.models import ColumnProfile, ProfilingResult, RegionProfile


def _find_sheet(result: ProfilingResult, name: str | None):
    if name is None and result.sheets:
        return result.sheets[0]
    for sheet in result.sheets:
        if sheet.sheet_name == name:
            return sheet
    return None


def _find_region(
    regions: tuple[RegionProfile, ...], expected: dict[str, Any]
) -> RegionProfile | None:
    if not regions:
        return None
    if "region_id" in expected:
        for region in regions:
            if region.region_id == expected["region_id"]:
                return region
        return None
    return regions[0]


def _find_column(
    columns: tuple[ColumnProfile, ...], expected: dict[str, Any]
) -> ColumnProfile | None:
    if "column_index" in expected:
        for col in columns:
            if col.column_index == expected["column_index"]:
                return col
        return None
    if "column_letter" in expected:
        for col in columns:
            if col.column_letter == expected["column_letter"]:
                return col
        return None
    return columns[0] if columns else None


def compare_profiling_expectations(
    *,
    scenario_id: str,
    result: ProfilingResult,
    expected: dict[str, Any],
) -> None:
    if not expected:
        return

    for idx, sheet_exp in enumerate(expected.get("sheets") or []):
        sheet = _find_sheet(result, sheet_exp.get("name"))
        path = f"expectations.profiling.sheets[{idx}]"
        if sheet is None:
            raise ExpectationMismatchError(scenario_id, path, sheet_exp, None)
        n = len(sheet.region_profiles)
        if "region_count_min" in sheet_exp and n < sheet_exp["region_count_min"]:
            raise ExpectationMismatchError(
                scenario_id, f"{path}.region_count_min", f">={sheet_exp['region_count_min']}", n
            )

        for r_idx, region_exp in enumerate(sheet_exp.get("regions") or []):
            # If regions empty but region_count_min only, skip column checks
            if not sheet.region_profiles and "columns" not in region_exp:
                continue
            region = _find_region(sheet.region_profiles, region_exp)
            rpath = f"{path}.regions[{r_idx}]"
            if region is None:
                raise ExpectationMismatchError(scenario_id, rpath, region_exp, None)

            for c_idx, col_exp in enumerate(region_exp.get("columns") or []):
                col = _find_column(region.columns, col_exp)
                cpath = f"{rpath}.columns[{c_idx}]"
                if col is None:
                    raise ExpectationMismatchError(scenario_id, cpath, col_exp, None)

                selected = col.logical_type_inference.selected_type.value
                if "logical_type" in col_exp:
                    wanted = col_exp["logical_type"]
                    alts = {item.type.value for item in col.logical_type_inference.alternatives}
                    compatible = {wanted}
                    if wanted == "decimal":
                        compatible.add("number")
                    if wanted == "number":
                        compatible.update({"decimal", "integer"})
                    if wanted == "percentage":
                        compatible.update({"decimal", "number"})
                    if wanted == "currency":
                        compatible.update({"decimal", "number"})
                    if wanted == "code":
                        compatible.add("identifier")
                    if wanted == "identifier":
                        compatible.update({"code", "uuid"})
                    if wanted == "uuid":
                        compatible.add("identifier")
                    if selected not in compatible and compatible.isdisjoint(alts):
                        raise ExpectationMismatchError(
                            scenario_id,
                            f"{cpath}.logical_type",
                            wanted,
                            {"selected": selected, "alternatives": sorted(alts)},
                        )
                if "minimum_confidence" in col_exp:
                    conf = col.logical_type_inference.confidence
                    wanted = col_exp.get("logical_type")
                    if wanted and wanted != selected:
                        alt_conf = next(
                            (
                                item.confidence
                                for item in col.logical_type_inference.alternatives
                                if item.type.value == wanted
                            ),
                            0.0,
                        )
                        conf = max(conf, alt_conf)
                    if conf < col_exp["minimum_confidence"]:
                        raise ExpectationMismatchError(
                            scenario_id,
                            f"{cpath}.minimum_confidence",
                            f">={col_exp['minimum_confidence']}",
                            conf,
                        )
                if (
                    "identifier_candidate" in col_exp
                    and col.identifier_analysis.is_candidate != col_exp["identifier_candidate"]
                ):
                    raise ExpectationMismatchError(
                        scenario_id,
                        f"{cpath}.identifier_candidate",
                        col_exp["identifier_candidate"],
                        col.identifier_analysis.is_candidate,
                    )
                if (
                    "categorical_candidate" in col_exp
                    and col.categorical_analysis.is_categorical_candidate
                    != col_exp["categorical_candidate"]
                ):
                    raise ExpectationMismatchError(
                        scenario_id,
                        f"{cpath}.categorical_candidate",
                        col_exp["categorical_candidate"],
                        col.categorical_analysis.is_categorical_candidate,
                    )
                if col_exp.get("has_anomalies") and not col.anomalies:
                    raise ExpectationMismatchError(
                        scenario_id, f"{cpath}.has_anomalies", True, False
                    )
                if "formula_count_min" in col_exp:
                    if col.statistics.formula_count < col_exp["formula_count_min"]:
                        raise ExpectationMismatchError(
                            scenario_id,
                            f"{cpath}.formula_count_min",
                            f">={col_exp['formula_count_min']}",
                            col.statistics.formula_count,
                        )
                if "null_count" in col_exp and col.statistics.null_count != col_exp["null_count"]:
                    raise ExpectationMismatchError(
                        scenario_id,
                        f"{cpath}.null_count",
                        col_exp["null_count"],
                        col.statistics.null_count,
                    )
                if (
                    "blank_string_count" in col_exp
                    and col.statistics.blank_string_count != col_exp["blank_string_count"]
                ):
                    raise ExpectationMismatchError(
                        scenario_id,
                        f"{cpath}.blank_string_count",
                        col_exp["blank_string_count"],
                        col.statistics.blank_string_count,
                    )
