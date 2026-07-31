"""Partial expectation comparator for Phase 2D relationship contracts."""

from __future__ import annotations

from typing import Any

from tests.inspection_compare import ExpectationMismatchError

from exceler.domain.relationships.models import (
    ForeignKeyCandidate,
    PrimaryKeyCandidate,
    RelationshipAnalysisResult,
)


def _sheet_pks(
    result: RelationshipAnalysisResult, name: str | None
) -> tuple[PrimaryKeyCandidate, ...]:
    if name is None and result.sheets:
        return result.sheets[0].primary_keys
    for sheet in result.sheets:
        if sheet.sheet_name == name:
            return sheet.primary_keys
    return ()


def _accepted_pks(pks: tuple[PrimaryKeyCandidate, ...]) -> tuple[PrimaryKeyCandidate, ...]:
    return tuple(pk for pk in pks if pk.accepted)


def _find_pk(
    pks: tuple[PrimaryKeyCandidate, ...], expected: dict[str, Any]
) -> PrimaryKeyCandidate | None:
    if "column_index" in expected:
        for pk in pks:
            if pk.column.column_index == expected["column_index"]:
                return pk
        return None
    return pks[0] if pks else None


def _find_fk(
    fks: tuple[ForeignKeyCandidate, ...], expected: dict[str, Any]
) -> ForeignKeyCandidate | None:
    for fk in fks:
        if "from_sheet" in expected and fk.from_column.sheet_name != expected["from_sheet"]:
            continue
        if (
            "from_column_index" in expected
            and fk.from_column.column_index != expected["from_column_index"]
        ):
            continue
        if "to_sheet" in expected and fk.to_column.sheet_name != expected["to_sheet"]:
            continue
        if (
            "to_column_index" in expected
            and fk.to_column.column_index != expected["to_column_index"]
        ):
            continue
        return fk
    return None


def compare_relationship_expectations(
    *,
    scenario_id: str,
    result: RelationshipAnalysisResult,
    expected: dict[str, Any],
) -> None:
    if not expected:
        return

    if "foreign_keys_min" in expected:
        n = len([fk for fk in result.foreign_keys if fk.accepted])
        if n < expected["foreign_keys_min"]:
            raise ExpectationMismatchError(
                scenario_id,
                "expectations.relationships.foreign_keys_min",
                f">={expected['foreign_keys_min']}",
                n,
            )

    for idx, sheet_exp in enumerate(expected.get("sheets") or []):
        path = f"expectations.relationships.sheets[{idx}]"
        name = sheet_exp.get("name")
        sheet = next((s for s in result.sheets if s.sheet_name == name), None)
        if sheet is None and name is not None:
            raise ExpectationMismatchError(scenario_id, path, sheet_exp, None)
        pks = _sheet_pks(result, name)
        accepted = _accepted_pks(pks)
        if "accepted_primary_keys_min" in sheet_exp:
            if len(accepted) < sheet_exp["accepted_primary_keys_min"]:
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{path}.accepted_primary_keys_min",
                    f">={sheet_exp['accepted_primary_keys_min']}",
                    len(accepted),
                )
        if "accepted_primary_keys_max" in sheet_exp:
            if len(accepted) > sheet_exp["accepted_primary_keys_max"]:
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{path}.accepted_primary_keys_max",
                    f"<={sheet_exp['accepted_primary_keys_max']}",
                    len(accepted),
                )
        if "composite_keys_min" in sheet_exp:
            composites = tuple(ck for ck in (sheet.composite_keys if sheet else ()) if ck.accepted)
            if len(composites) < sheet_exp["composite_keys_min"]:
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{path}.composite_keys_min",
                    f">={sheet_exp['composite_keys_min']}",
                    len(composites),
                )
        if "pk_rank_order" in sheet_exp:
            expected_order = sheet_exp["pk_rank_order"]
            ranked = [pk.column.column_index for pk in accepted]
            if ranked[: len(expected_order)] != expected_order:
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{path}.pk_rank_order",
                    expected_order,
                    ranked,
                )
        for p_idx, pk_exp in enumerate(sheet_exp.get("primary_keys") or []):
            pk = _find_pk(pks, pk_exp)
            ppath = f"{path}.primary_keys[{p_idx}]"
            if pk is None:
                raise ExpectationMismatchError(scenario_id, ppath, pk_exp, None)
            if "accepted" in pk_exp and pk.accepted is not bool(pk_exp["accepted"]):
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{ppath}.accepted",
                    pk_exp["accepted"],
                    pk.accepted,
                )
            if "key_kind" in pk_exp and pk.key_kind.value != pk_exp["key_kind"]:
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{ppath}.key_kind",
                    pk_exp["key_kind"],
                    pk.key_kind.value,
                )
            if "key_kind_not" in pk_exp and pk.key_kind.value == pk_exp["key_kind_not"]:
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{ppath}.key_kind_not",
                    f"!={pk_exp['key_kind_not']}",
                    pk.key_kind.value,
                )
            if "minimum_confidence" in pk_exp and pk.confidence < pk_exp["minimum_confidence"]:
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{ppath}.minimum_confidence",
                    f">={pk_exp['minimum_confidence']}",
                    pk.confidence,
                )
            if "maximum_confidence" in pk_exp and pk.confidence > pk_exp["maximum_confidence"]:
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{ppath}.maximum_confidence",
                    f"<={pk_exp['maximum_confidence']}",
                    pk.confidence,
                )
            if "minimum_score" in pk_exp and pk.score < pk_exp["minimum_score"]:
                raise ExpectationMismatchError(
                    scenario_id,
                    f"{ppath}.minimum_score",
                    f">={pk_exp['minimum_score']}",
                    pk.score,
                )
            if "rejection_reason" in pk_exp:
                reason = pk_exp["rejection_reason"]
                if reason not in pk.rejection_reasons:
                    raise ExpectationMismatchError(
                        scenario_id,
                        f"{ppath}.rejection_reason",
                        reason,
                        list(pk.rejection_reasons),
                    )

    for f_idx, fk_exp in enumerate(expected.get("foreign_keys") or []):
        fpath = f"expectations.relationships.foreign_keys[{f_idx}]"
        fk = _find_fk(result.foreign_keys, fk_exp)
        if fk is None:
            raise ExpectationMismatchError(scenario_id, fpath, fk_exp, None)
        if "accepted" in fk_exp and fk.accepted is not bool(fk_exp["accepted"]):
            raise ExpectationMismatchError(
                scenario_id,
                f"{fpath}.accepted",
                fk_exp["accepted"],
                fk.accepted,
            )
        if "minimum_inclusion" in fk_exp and fk.inclusion_ratio < fk_exp["minimum_inclusion"]:
            raise ExpectationMismatchError(
                scenario_id,
                f"{fpath}.minimum_inclusion",
                f">={fk_exp['minimum_inclusion']}",
                fk.inclusion_ratio,
            )
        if "minimum_confidence" in fk_exp and fk.confidence < fk_exp["minimum_confidence"]:
            raise ExpectationMismatchError(
                scenario_id,
                f"{fpath}.minimum_confidence",
                f">={fk_exp['minimum_confidence']}",
                fk.confidence,
            )
        if "cardinality" in fk_exp and fk.cardinality.value != fk_exp["cardinality"]:
            raise ExpectationMismatchError(
                scenario_id,
                f"{fpath}.cardinality",
                fk_exp["cardinality"],
                fk.cardinality.value,
            )
        if fk_exp.get("has_orphans") and fk.orphan_count <= 0:
            raise ExpectationMismatchError(scenario_id, f"{fpath}.has_orphans", True, False)
