"""Phase 2D relationship contract and unit tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from tests.generators.catalog import ALL_SPECS
from tests.generators.workbook_factory import workbook_path
from tests.relationships_compare import compare_relationship_expectations

from exceler.application.profiling.profiler import DeterministicRegionProfiler
from exceler.application.regions.heuristic_detector import HeuristicRegionDetector
from exceler.application.relationships.analyzer import DeterministicRelationshipAnalyzer
from exceler.application.relationships.serialization import relationships_to_dict
from exceler.domain.profiling.models import ProfilingResult
from exceler.domain.relationships.errors import RelationshipInputMismatchError
from exceler.domain.relationships.options import RELATIONSHIP_SCHEMA_VERSION, RelationshipOptions
from exceler.domain.workbook.models import WorkbookInspectionOptions
from exceler.infrastructure.workbook.local_source import LocalWorkbookSource
from exceler.infrastructure.workbook.openpyxl_reader import OpenPyxlWorkbookReader

pytestmark = pytest.mark.unit

READER = OpenPyxlWorkbookReader()
DETECTOR = HeuristicRegionDetector()
PROFILER = DeterministicRegionProfiler()
ANALYZER = DeterministicRelationshipAnalyzer()

REL_SCENARIO_IDS = {
    "rel_simple_primary_key",
    "rel_duplicate_identifier",
    "rel_composite_key",
    "rel_customers_orders",
    "rel_invoice_header_lines",
    "rel_orphan_and_partial",
    "rel_bridge_table",
    "rel_integer_unique_not_surrogate",
    "rel_numeric_customer_id_fk",
    "rel_matching_measures_no_relation",
    "rel_measure_into_identifier_no_fk",
    "rel_incompatible_product_customer",
    "rel_alias_client_customer",
    "rel_alias_article_product",
    "rel_insufficient_bare_id_fk",
    "rel_pk_ranking",
}


def _run(path: Path, **rel_kwargs: object):
    inspection = READER.inspect(LocalWorkbookSource(path), WorkbookInspectionOptions())
    regions = DETECTOR.detect(inspection)
    profiling = PROFILER.profile(inspection, regions)
    options = RelationshipOptions(**rel_kwargs) if rel_kwargs else RelationshipOptions()
    result = ANALYZER.analyze(inspection, regions, profiling, options)
    return inspection, regions, profiling, result


def test_contract_relationships_against_expected() -> None:
    for spec in ALL_SPECS:
        expected = spec.expected_skeleton.get("relationships")
        if not expected:
            continue
        path = workbook_path(spec)
        assert path.exists(), f"missing workbook for {spec.scenario_id}"
        _i, _r, _p, result = _run(path)
        compare_relationship_expectations(
            scenario_id=spec.scenario_id,
            result=result,
            expected=expected,
        )


@pytest.mark.parametrize("scenario_id", sorted(REL_SCENARIO_IDS))
def test_relationship_scenarios_registered(scenario_id: str) -> None:
    assert scenario_id in {spec.scenario_id for spec in ALL_SPECS}


def test_relationship_modules_never_import_openpyxl() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "exceler" / "application" / "relationships"
    domain = Path(__file__).resolve().parents[1] / "src" / "exceler" / "domain" / "relationships"
    for path in list(root.rglob("*.py")) + list(domain.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] != "openpyxl" for alias in node.names)
                assert all(alias.name.split(".")[0] != "pandas" for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] != "openpyxl"
                assert node.module.split(".")[0] != "pandas"


def test_relationships_deterministic() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_customers_orders"))
    _a = _run(path)[3]
    _b = _run(path)[3]
    assert relationships_to_dict(_a) == relationships_to_dict(_b)
    assert _a.relationship_schema_version == RELATIONSHIP_SCHEMA_VERSION


def test_hash_mismatch_raises() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_simple_primary_key"))
    inspection, regions, profiling, _ = _run(path)
    bad = ProfilingResult(
        workbook_hash="0" * 64,
        inspector_version=profiling.inspector_version,
        region_detector_version=profiling.region_detector_version,
        regions_schema_version=profiling.regions_schema_version,
        profiler_version=profiling.profiler_version,
        profiling_schema_version=profiling.profiling_schema_version,
        sheets=profiling.sheets,
        warnings=profiling.warnings,
        limitations=profiling.limitations,
    )
    with pytest.raises(RelationshipInputMismatchError):
        ANALYZER.analyze(inspection, regions, bad)


def test_customers_orders_fk_inclusion() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_customers_orders"))
    _i, _r, _p, result = _run(path)
    assert result.foreign_keys
    fk = next(
        item
        for item in result.foreign_keys
        if item.from_column.sheet_name == "Orders" and item.to_column.sheet_name == "Customers"
    )
    assert fk.inclusion_ratio >= 0.99
    assert fk.orphan_count == 0


def test_composite_key_detected() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_composite_key"))
    _i, _r, _p, result = _run(path)
    assert any(ck.accepted for sheet in result.sheets for ck in sheet.composite_keys)


def test_duplicate_identifier_rejected() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_duplicate_identifier"))
    _i, _r, _p, result = _run(path)
    sheet = result.sheets[0]
    assert not any(pk.accepted for pk in sheet.primary_keys)
    dup = next(pk for pk in sheet.primary_keys if pk.column.column_index == 1)
    assert "below_min_pk_distinct_ratio" in dup.rejection_reasons


def test_integer_unique_not_surrogate() -> None:
    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "rel_integer_unique_not_surrogate")
    )
    _i, _r, _p, result = _run(path)
    pk = next(pk for pk in result.sheets[0].primary_keys if pk.column.column_index == 1)
    assert pk.key_kind.value == "primary"
    assert pk.key_kind.value != "surrogate"
    assert pk.accepted is False
    assert "insufficient_independent_identifier_evidence" in pk.rejection_reasons


def test_incoming_fk_alone_does_not_accept_numeric_pk() -> None:
    from exceler.application.relationships.identifier_signals import (
        has_independent_identifier_evidence,
    )
    from exceler.application.relationships.value_index import build_column_value_sets

    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "rel_matching_measures_no_relation")
    )
    inspection, regions, profiling, result = _run(path)
    columns = build_column_value_sets(inspection, regions, profiling, RelationshipOptions())
    qty = next(col for col in columns if col.ref.effective_name == "Qty")
    assert has_independent_identifier_evidence(qty) is False
    assert not any(fk.accepted for fk in result.foreign_keys)
    for sheet in result.sheets:
        assert not any(pk.accepted for pk in sheet.primary_keys)


def test_numeric_customer_id_accepted_via_fk_parent() -> None:
    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "rel_numeric_customer_id_fk")
    )
    _i, _r, _p, result = _run(path)
    customers = next(sheet for sheet in result.sheets if sheet.sheet_name == "Customers")
    pk = next(item for item in customers.primary_keys if item.column.column_index == 1)
    assert pk.accepted is True
    assert pk.key_kind.value == "primary"
    assert pk.key_kind.value != "surrogate"
    assert any(item.code == "independent_identifier_evidence" for item in pk.evidence)
    fk = next(
        item
        for item in result.foreign_keys
        if item.from_column.sheet_name == "Orders"
        and item.to_column.sheet_name == "Customers"
        and item.accepted
    )
    assert fk.inclusion_ratio >= 0.99
    reverse = [
        item
        for item in result.foreign_keys
        if item.from_column.sheet_name == "Customers"
        and item.to_column.sheet_name == "Orders"
        and item.accepted
    ]
    assert reverse == []
    amount = next(
        item
        for sheet in result.sheets
        if sheet.sheet_name == "Orders"
        for item in sheet.primary_keys
        if item.column.column_index == 3
    )
    assert amount.accepted is False


def test_matching_measures_reject_both_fk_directions() -> None:
    from exceler.domain.relationships.enums import GraphEdgeKind

    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "rel_matching_measures_no_relation")
    )
    _i, _r, _p, result = _run(path)
    pairs = {
        (fk.from_column.sheet_name, fk.to_column.sheet_name, fk.accepted)
        for fk in result.foreign_keys
        if {fk.from_column.sheet_name, fk.to_column.sheet_name} == {"WarehouseA", "WarehouseB"}
    }
    assert ("WarehouseA", "WarehouseB", True) not in pairs
    assert ("WarehouseB", "WarehouseA", True) not in pairs
    for fk in result.foreign_keys:
        if {fk.from_column.sheet_name, fk.to_column.sheet_name} == {"WarehouseA", "WarehouseB"}:
            assert fk.accepted is False
            assert (
                "insufficient_independent_identifier_evidence" in fk.rejection_reasons
                or "ambiguous_relationship_direction" in fk.rejection_reasons
            )
    rel_edges = [
        edge
        for edge in result.graph.edges
        if edge.kind in {GraphEdgeKind.CANDIDATE_FOREIGN_KEY, GraphEdgeKind.CANDIDATE_RELATIONSHIP}
    ]
    assert rel_edges == []


def test_relationship_support_reinforces_but_does_not_create_acceptance() -> None:
    from exceler.application.relationships.keys import discover_primary_keys
    from exceler.application.relationships.value_index import build_column_value_sets

    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "rel_numeric_customer_id_fk")
    )
    inspection, regions, profiling, _ = _run(path)
    columns = build_column_value_sets(inspection, regions, profiling, RelationshipOptions())
    customer_id = next(
        col for col in columns if col.ref.sheet_name == "Customers" and col.ref.column_index == 1
    )
    without = discover_primary_keys(columns, options=RelationshipOptions())
    pk_without = next(pk for pk in without if pk.column.column_id == customer_id.ref.column_id)
    assert pk_without.accepted is True
    with_support = discover_primary_keys(
        columns,
        options=RelationshipOptions(),
        referenced_column_ids=frozenset({customer_id.ref.column_id}),
    )
    pk_with = next(pk for pk in with_support if pk.column.column_id == customer_id.ref.column_id)
    assert pk_with.accepted is True
    assert pk_with.score >= pk_without.score
    assert any(item.code == "fk_parent_reference" for item in pk_with.evidence)

    path_m = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "rel_matching_measures_no_relation")
    )
    inspection_m, regions_m, profiling_m, _ = _run(path_m)
    cols_m = build_column_value_sets(inspection_m, regions_m, profiling_m, RelationshipOptions())
    qty = next(col for col in cols_m if col.ref.effective_name == "Qty")
    fake = discover_primary_keys(
        cols_m,
        options=RelationshipOptions(),
        referenced_column_ids=frozenset({qty.ref.column_id}),
    )
    qty_pk = next(pk for pk in fake if pk.column.column_id == qty.ref.column_id)
    assert qty_pk.accepted is False
    assert "insufficient_independent_identifier_evidence" in qty_pk.rejection_reasons


def test_analysis_order_deterministic_for_measures() -> None:
    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "rel_matching_measures_no_relation")
    )
    a = relationships_to_dict(_run(path)[3])
    b = relationships_to_dict(_run(path)[3])
    assert a == b


def test_measure_into_identifier_rejected_preserves_customer_fk() -> None:
    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "rel_measure_into_identifier_no_fk")
    )
    _i, _r, _p, result = _run(path)
    amount_fk = next(
        item
        for item in result.foreign_keys
        if item.from_column.sheet_name == "Sales"
        and item.from_column.column_index == 2
        and item.to_column.sheet_name == "Customers"
        and item.to_column.column_index == 1
    )
    assert amount_fk.accepted is False
    assert "insufficient_child_reference_evidence" in amount_fk.rejection_reasons

    customer_fk = next(
        item
        for item in result.foreign_keys
        if item.from_column.sheet_name == "Orders"
        and item.from_column.column_index == 2
        and item.to_column.sheet_name == "Customers"
        and item.to_column.column_index == 1
        and item.accepted
    )
    assert customer_fk.inclusion_ratio >= 0.99


def test_header_token_boundaries_reject_suffix_false_positives() -> None:
    from exceler.application.relationships.identifier_signals import (
        SemanticCompatibilityStatus,
        extract_identifier_semantic_signal,
        header_suggests_identifier,
        header_tokens,
        reference_target_semantically_compatible,
    )

    assert header_tokens("CustomerId") == ("customer", "id")
    assert header_tokens("customer_id") == ("customer", "id")
    assert header_tokens("CUSTOMER-ID") == ("customer", "id")
    assert header_tokens("IdCustomer") == ("id", "customer")
    assert header_tokens("ClientIdentifier") == ("client", "identifier")
    assert header_tokens("CodigoCliente") == ("codigo", "cliente")
    assert header_tokens("PedidoCodigo") == ("pedido", "codigo")
    assert header_tokens("Paid") == ("paid",)
    assert header_tokens("Valid") == ("valid",)
    assert header_tokens("Grid") == ("grid",)
    assert header_tokens("Codec") == ("codec",)

    assert header_suggests_identifier("CustomerId") is True
    assert header_suggests_identifier("customer_id") is True
    assert header_suggests_identifier("PersonCode") is True
    assert header_suggests_identifier("Código") is True
    assert header_suggests_identifier("Id") is True
    assert header_suggests_identifier("paid") is False
    assert header_suggests_identifier("valid") is False
    assert header_suggests_identifier("grid") is False
    assert header_suggests_identifier("Amount") is False
    assert header_suggests_identifier("Qty") is False
    assert header_suggests_identifier("Codec") is False

    customer = extract_identifier_semantic_signal("CustomerId")
    assert customer.canonical_entity == "customer"
    assert customer.entity_tokens == ("customer",)
    assert customer.structural_tokens == ("id",)

    id_customer = extract_identifier_semantic_signal("IdCustomer")
    assert id_customer.canonical_entity == "customer"

    codigo_cliente = extract_identifier_semantic_signal("CodigoCliente")
    assert codigo_cliente.canonical_entity == "customer"

    product = extract_identifier_semantic_signal("ProductId")
    assert product.canonical_entity == "product"
    assert (
        reference_target_semantically_compatible(product, customer).status
        is SemanticCompatibilityStatus.INCOMPATIBLE
    )

    client = extract_identifier_semantic_signal("ClientId")
    assert (
        reference_target_semantically_compatible(client, customer).status
        is SemanticCompatibilityStatus.COMPATIBLE
    )

    article = extract_identifier_semantic_signal("ArticleCode")
    product_code = extract_identifier_semantic_signal("ProductCode")
    assert (
        reference_target_semantically_compatible(article, product_code).status
        is SemanticCompatibilityStatus.COMPATIBLE
    )

    bare_id = extract_identifier_semantic_signal("Id")
    assert bare_id.has_entity_evidence is False
    assert (
        reference_target_semantically_compatible(bare_id, customer).status
        is SemanticCompatibilityStatus.INSUFFICIENT
    )


def test_incompatible_product_customer_rejected_both_directions() -> None:
    from exceler.domain.relationships.enums import GraphEdgeKind

    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "rel_incompatible_product_customer")
    )
    _i, _r, _p, result = _run(path)
    customers = next(sheet for sheet in result.sheets if sheet.sheet_name == "Customers")
    assert any(pk.accepted and pk.column.column_index == 1 for pk in customers.primary_keys)

    forward = next(
        fk
        for fk in result.foreign_keys
        if fk.from_column.sheet_name == "Products"
        and fk.from_column.column_index == 2
        and fk.to_column.sheet_name == "Customers"
        and fk.to_column.column_index == 1
    )
    assert forward.accepted is False
    assert "incompatible_reference_target_semantics" in forward.rejection_reasons
    assert any(item.code == "semantic_entity_mismatch" for item in forward.evidence)

    reverse_accepted = [
        fk
        for fk in result.foreign_keys
        if fk.from_column.sheet_name == "Customers"
        and fk.to_column.sheet_name == "Products"
        and fk.accepted
    ]
    assert reverse_accepted == []
    reverse = next(
        fk
        for fk in result.foreign_keys
        if fk.from_column.sheet_name == "Customers"
        and fk.to_column.sheet_name == "Products"
        and fk.from_column.column_index == 1
        and fk.to_column.column_index == 2
    )
    assert reverse.accepted is False
    assert "incompatible_reference_target_semantics" in reverse.rejection_reasons
    assert not any(
        edge.kind in {GraphEdgeKind.CANDIDATE_FOREIGN_KEY, GraphEdgeKind.CANDIDATE_RELATIONSHIP}
        for edge in result.graph.edges
    )


def test_alias_client_customer_accepted_with_semantic_evidence() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_alias_client_customer"))
    _i, _r, _p, result = _run(path)
    fk = next(
        item
        for item in result.foreign_keys
        if item.from_column.sheet_name == "Orders"
        and item.to_column.sheet_name == "Customers"
        and item.accepted
    )
    assert fk.inclusion_ratio >= 0.99
    evidence = next(item for item in fk.evidence if item.code == "semantic_entity_compatibility")
    assert evidence.details["status"] == "compatible"
    assert evidence.details["child_canonical_entity"] == "customer"
    assert evidence.details["parent_canonical_entity"] == "customer"


def test_alias_article_product_accepted() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_alias_article_product"))
    _i, _r, _p, result = _run(path)
    fk = next(
        item
        for item in result.foreign_keys
        if item.from_column.sheet_name == "OrderLines"
        and item.to_column.sheet_name == "Products"
        and item.accepted
    )
    assert fk.inclusion_ratio >= 0.99
    evidence = next(item for item in fk.evidence if item.code == "semantic_entity_compatibility")
    assert evidence.details["shared_entities"] == ["product"]


def test_insufficient_bare_id_rejected() -> None:
    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "rel_insufficient_bare_id_fk")
    )
    _i, _r, _p, result = _run(path)
    assert not any(fk.accepted for fk in result.foreign_keys)
    fk = next(
        item
        for item in result.foreign_keys
        if item.from_column.sheet_name == "Source" and item.to_column.sheet_name == "Customers"
    )
    assert "insufficient_reference_target_semantics" in fk.rejection_reasons


def test_semantic_incompatibility_beats_perfect_inclusion() -> None:
    path = workbook_path(
        next(s for s in ALL_SPECS if s.scenario_id == "rel_incompatible_product_customer")
    )
    _i, _r, _p, result = _run(path)
    fk = next(
        item
        for item in result.foreign_keys
        if item.from_column.effective_name == "ProductId"
        and item.to_column.effective_name == "CustomerId"
    )
    assert fk.inclusion_ratio >= 0.99
    assert fk.accepted is False
    assert "incompatible_reference_target_semantics" in fk.rejection_reasons
    assert fk.confidence < 1.0 or not fk.accepted


def test_sheet_order_permutation_preserves_alias_result() -> None:
    from exceler.application.relationships.serialization import relationships_to_dict

    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_alias_client_customer"))
    a = relationships_to_dict(_run(path)[3])
    b = relationships_to_dict(_run(path)[3])
    assert a == b
    assert a["relationship_engine_version"] == "2D.6"


def test_pk_ranking_prefers_code_over_text() -> None:
    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_pk_ranking"))
    _i, _r, _p, result = _run(path)
    accepted = [pk for pk in result.sheets[0].primary_keys if pk.accepted]
    assert accepted
    assert accepted[0].column.column_index == 1
    name_pk = next(pk for pk in result.sheets[0].primary_keys if pk.column.column_index == 2)
    assert name_pk.accepted is False
    assert "penalized_logical_type" in name_pk.rejection_reasons


def test_confidence_calibrated_against_max_weight() -> None:
    from exceler.application.relationships.evidence import confidence_from_evidence
    from exceler.domain.relationships.models import RelationshipEvidenceItem

    items = [
        RelationshipEvidenceItem("a", 0.35, "only distinct"),
        RelationshipEvidenceItem("b", 0.25, "only non-null"),
    ]
    # Against max 1.0, missing identifier+logical → score 0.60, not 1.0.
    score = confidence_from_evidence(items, max_positive_weight=1.0)
    assert 0.59 <= score <= 0.61


def test_cli_workbook_relationships_json(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from exceler.cli.main import app

    path = workbook_path(next(s for s in ALL_SPECS if s.scenario_id == "rel_simple_primary_key"))
    out = tmp_path / "relationships.json"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "workbook",
            "relationships",
            str(path),
            "--format",
            "json",
            "--pretty",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["relationship_schema_version"] == RELATIONSHIP_SCHEMA_VERSION
    assert payload["sheets"]
