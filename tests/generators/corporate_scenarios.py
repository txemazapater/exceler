from __future__ import annotations

import random
from typing import Any

from openpyxl import Workbook
from tests.generators import DEFAULT_SEED
from tests.generators.workbook_factory import ScenarioSpec, bold_header, new_workbook, write_matrix

SCENARIO_CATEGORY = "scenarios"
SCENARIO_PREFIX = "workbooks/scenarios/hell_erp"


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def build_clientes(seed: int) -> Workbook:
    wb = new_workbook(sheet_title="Clientes")
    ws = wb.active
    assert ws is not None
    # Deliberate anomalies: leading zeros as text, duplicate, padded spaces, S/N boolean.
    rows: list[list[Any]] = [
        ["CodCliente", "Nombre", "Activo", "Ciudad"],
        ["001", "Acme Norte", "S", "Madrid"],
        ["002", "Beta Sur", "S", "Sevilla"],
        ["003", " Gamma Este ", "N", "Valencia"],  # spaces in name
        ["001", "Acme Norte DUP", "S", "Madrid"],  # duplicate key
        ["004", "Delta Oeste", "S", "Bilbao"],
    ]
    write_matrix(ws, rows)
    bold_header(ws, 1, 4)
    notes = wb.create_sheet("Notas")
    notes["A1"] = "Hoja auxiliar no tabular — no interpretar como maestro"
    notes["A3"] = "Contacto ficticio: nadie@example.invalid"
    return wb


def build_articulos(seed: int) -> Workbook:
    rng = _rng(seed + 1)
    wb = new_workbook(sheet_title="Articulos")
    ws = wb.active
    assert ws is not None
    rows: list[list[Any]] = [
        ["CodArticulo", "Descripcion", "Precio", "Activo"],
        ["A-01", "Tuerca M6", 0.15, "S"],
        ["A-02", "Tornillo M6", 0.08, "S"],
        ["A-03", "Arandela", 0.05, "N"],  # inactive
        ["A-04", "Pasador", 0.22, "S"],
        [None, "Sin codigo", rng.choice([0.01, 0.02]), "S"],  # null key allowed anomaly
    ]
    write_matrix(ws, rows)
    bold_header(ws, 1, 4)
    return wb


def build_pedidos(seed: int) -> Workbook:
    wb = new_workbook(sheet_title="Pedidos")
    ws = wb.active
    assert ws is not None
    rows: list[list[Any]] = [
        ["NumPedido", "Cliente", "FechaPedido", "Estado"],
        ["P-100", "001", "2024-01-15", "Cerrado"],
        ["P-101", "002", "15/02/2024", "Abierto"],  # date as text variant
        ["P-102", "999", "2024-03-01", "Abierto"],  # nonexistent customer
        ["P-103", " 003", "2024-03-10", "Cerrado"],  # spaced customer ref
    ]
    write_matrix(ws, rows)
    bold_header(ws, 1, 4)
    return wb


def build_lineas_pedido(seed: int) -> Workbook:
    wb = new_workbook(sheet_title="Lineas")
    ws = wb.active
    assert ws is not None
    rows: list[list[Any]] = [
        ["Pedido", "Articulo", "Cantidad", "Importe"],
        ["P-100", "A-01", 10, 1.5],
        ["P-100", "A-02", 5, 0.4],
        ["P-101", "A-04", 1, 0.22],
        ["P-102", "A-01", 2, 0.3],
        ["P-103", "A-03", 1, 0.05],
        ["TOTAL", None, None, 2.47],  # totals row noise
    ]
    write_matrix(ws, rows)
    bold_header(ws, 1, 4)
    return wb


def build_facturas(seed: int) -> Workbook:
    wb = new_workbook(sheet_title="Facturas")
    ws = wb.active
    assert ws is not None
    # Same concept as CodCliente / Cliente but different column name.
    rows: list[list[Any]] = [
        ["NumFactura", "CodigoCliente", "Pedido", "FechaFactura", "Total"],
        ["F-500", "001", "P-100", "2024-01-20", 1.9],
        ["F-501", "002", "P-101", "2024-02-20", 0.22],
        ["F-502", "001", "P-100", "2024-01-21", None],  # null amount
    ]
    write_matrix(ws, rows)
    bold_header(ws, 1, 5)
    return wb


CORPORATE_SPECS: list[ScenarioSpec] = [
    ScenarioSpec(
        scenario_id="hell_erp_clientes",
        category=SCENARIO_CATEGORY,
        description="Maestro de clientes sintético con duplicado y ceros iniciales",
        relative_workbook=f"{SCENARIO_PREFIX}/clientes.xlsx",
        generator_name="corporate_scenarios.build_clientes",
        seed=DEFAULT_SEED,
        intentions=[
            "CodCliente conserva ceros iniciales como texto",
            "Existe un CodCliente duplicado (001)",
            "Activo usa valores S/N",
            "Existe hoja auxiliar no tabular",
            "Nombre con espacios alrededor en un registro",
        ],
        features=[
            "text_code",
            "boolean_candidate",
            "duplicate_key",
            "auxiliary_sheet",
            "whitespace",
        ],
        expected_skeleton={
            "worksheets": 2,
            "relationships": {
                "referenced_by": ["hell_erp_pedidos", "hell_erp_facturas"],
                "key_concept": "customer_code",
            },
        },
    ),
    ScenarioSpec(
        scenario_id="hell_erp_articulos",
        category=SCENARIO_CATEGORY,
        description="Catálogo de artículos con nulo e inactivo",
        relative_workbook=f"{SCENARIO_PREFIX}/articulos.xlsx",
        generator_name="corporate_scenarios.build_articulos",
        seed=DEFAULT_SEED,
        intentions=[
            "Un artículo inactivo",
            "Una fila con CodArticulo nulo",
            "Precios numéricos",
        ],
        features=["null_key", "inactive_flag", "catalog"],
    ),
    ScenarioSpec(
        scenario_id="hell_erp_pedidos",
        category=SCENARIO_CATEGORY,
        description="Pedidos con cliente inexistente y fecha textual",
        relative_workbook=f"{SCENARIO_PREFIX}/pedidos.xlsx",
        generator_name="corporate_scenarios.build_pedidos",
        seed=DEFAULT_SEED,
        intentions=[
            "Cliente referencia CodCliente de clientes",
            "Una referencia de cliente inexistente (999)",
            "Una fecha almacenada como texto dd/mm/yyyy",
            "Un identificador de cliente con espacios",
        ],
        features=["fk_candidate", "missing_reference", "date_as_text", "whitespace_key"],
        expected_skeleton={
            "relationships": {
                "customer_column": "Cliente",
                "targets": ["hell_erp_clientes.CodCliente"],
            }
        },
    ),
    ScenarioSpec(
        scenario_id="hell_erp_lineas_pedido",
        category=SCENARIO_CATEGORY,
        description="Líneas de pedido con fila de totales",
        relative_workbook=f"{SCENARIO_PREFIX}/lineas_pedido.xlsx",
        generator_name="corporate_scenarios.build_lineas_pedido",
        seed=DEFAULT_SEED,
        intentions=[
            "Pedido referencia NumPedido",
            "Articulo referencia CodArticulo",
            "Última fila es TOTAL no detalle",
        ],
        features=["fk_candidate", "totals_row", "line_items"],
    ),
    ScenarioSpec(
        scenario_id="hell_erp_facturas",
        category=SCENARIO_CATEGORY,
        description="Facturas con nombre de columna distinto para el mismo concepto de cliente",
        relative_workbook=f"{SCENARIO_PREFIX}/facturas.xlsx",
        generator_name="corporate_scenarios.build_facturas",
        seed=DEFAULT_SEED,
        intentions=[
            "CodigoCliente equivale semánticamente a CodCliente/Cliente",
            "Pedido referencia NumPedido",
            "Un total nulo permitido",
        ],
        features=["synonym_column", "fk_candidate", "nullable_amount"],
    ),
]


BUILDERS: dict[str, object] = {
    "corporate_scenarios.build_clientes": build_clientes,
    "corporate_scenarios.build_articulos": build_articulos,
    "corporate_scenarios.build_pedidos": build_pedidos,
    "corporate_scenarios.build_lineas_pedido": build_lineas_pedido,
    "corporate_scenarios.build_facturas": build_facturas,
}
