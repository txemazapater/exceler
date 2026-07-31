"""Independent vs relationship-derived identity signals (Phase 2D.4)."""

from __future__ import annotations

import re

from exceler.application.relationships.value_index import ColumnValueSet
from exceler.domain.profiling.enums import LogicalValueType
from exceler.domain.profiling.models import IdentifierAnalysis

_PREFERRED_LOGICAL = {
    LogicalValueType.IDENTIFIER,
    LogicalValueType.UUID,
    LogicalValueType.CODE,
}

# Cardinality-only reasons from 2C — not enough to prove identity for numerics.
_CARDINALITY_IDENTIFIER_REASONS = frozenset(
    {
        "high_distinct_ratio",
        "high_non_null_ratio",
    }
)

# Controlled header tokens (identity gate, not PK/FK ranking among peers).
_IDENTIFIER_HEADER_RE = re.compile(
    r"(?i)"
    r"(?:^id$|(?:^|_)id$|id$|"
    r"^code$|(?:^|_)code$|code$|"
    r"codigo|código|"
    r"uuid|guid|"
    r"clave|"
    r"(?:customer|order|product|article|invoice|client|pedido|articulo)id|"
    r"id(?:cliente|pedido|articulo)|"
    r"codigo(?:cliente|articulo|pedido))"
)


def header_suggests_identifier(effective_name: str) -> bool:
    """True when the header carries controlled identifier semantics."""
    name = effective_name.strip()
    if not name:
        return False
    compact = re.sub(r"[\s_\-]+", "", name)
    return bool(_IDENTIFIER_HEADER_RE.search(name) or _IDENTIFIER_HEADER_RE.search(compact))


def has_rich_identifier_analysis(identifier: IdentifierAnalysis) -> bool:
    """2C identifier candidacy with signals beyond uniqueness/non-null alone."""
    if not identifier.is_candidate:
        return False
    return any(reason not in _CARDINALITY_IDENTIFIER_REASONS for reason in identifier.reasons)


def has_independent_identifier_evidence(column: ColumnValueSet) -> bool:
    """Identity evidence that does not depend on 2D FK/PK circular inference."""
    logical = column.profile.logical_type_inference.selected_type
    if logical in _PREFERRED_LOGICAL:
        return True
    if header_suggests_identifier(column.ref.effective_name):
        return True
    if has_rich_identifier_analysis(column.profile.identifier_analysis):
        return True
    return False


def has_relationship_support(
    column_id: str,
    *,
    referenced_column_ids: frozenset[str],
) -> bool:
    """True when an accepted FK targets this column (relationship support only)."""
    return column_id in referenced_column_ids
