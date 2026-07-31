"""Independent vs relationship-derived identity signals (Phase 2D.4 / 2D.5)."""

from __future__ import annotations

import re
import unicodedata

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

# Whole-token identifier vocabulary (2D.5: token boundaries, not suffix match).
_IDENTIFIER_TOKENS = frozenset(
    {
        "id",
        "code",
        "codigo",
        "uuid",
        "guid",
        "clave",
    }
)

# Compact compounds when CamelCase / separators were flattened (allowlist only).
_COMPACT_IDENTIFIER_RE = re.compile(
    r"^(?:"
    r"(?:customer|order|product|article|invoice|client|pedido|articulo|"
    r"parent|child|student|course|sale|person|line)id|"
    r"id(?:cliente|pedido|articulo)|"
    r"codigo(?:cliente|articulo|pedido)?"
    r")$"
)

_SPLIT_CAMEL_LOWER_UPPER = re.compile(r"([a-z0-9])([A-Z])")
_SPLIT_CAMEL_ACRONYM = re.compile(r"([A-Z]+)([A-Z][a-z])")
_SPLIT_SEPARATORS = re.compile(r"[\s_\-/\\.:]+")


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def header_tokens(effective_name: str) -> tuple[str, ...]:
    """Split a header into lowercase tokens on CamelCase and separators."""
    name = effective_name.strip()
    if not name:
        return ()
    spaced = _SPLIT_CAMEL_LOWER_UPPER.sub(r"\1 \2", name)
    spaced = _SPLIT_CAMEL_ACRONYM.sub(r"\1 \2", spaced)
    parts = _SPLIT_SEPARATORS.split(spaced)
    return tuple(_strip_accents(part).lower() for part in parts if part)


def header_suggests_identifier(effective_name: str) -> bool:
    """True when a controlled identifier token appears as a whole token."""
    tokens = header_tokens(effective_name)
    if any(token in _IDENTIFIER_TOKENS for token in tokens):
        return True
    compact = "".join(tokens)
    return bool(compact and _COMPACT_IDENTIFIER_RE.match(compact))


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


def has_child_reference_evidence(column: ColumnValueSet) -> bool:
    """FK child must look like a reference (type or header), not a measure."""
    logical = column.profile.logical_type_inference.selected_type
    if logical in _PREFERRED_LOGICAL:
        return True
    return header_suggests_identifier(column.ref.effective_name)


def has_relationship_support(
    column_id: str,
    *,
    referenced_column_ids: frozenset[str],
) -> bool:
    """True when an accepted FK targets this column (relationship support only)."""
    return column_id in referenced_column_ids
