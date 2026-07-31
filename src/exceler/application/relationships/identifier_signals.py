"""Identity, reference, and header-entity semantic signals (Phase 2D.4–2D.6)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

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

# Whole-token structural vocabulary (identity gate + entity extraction).
STRUCTURAL_TOKENS = frozenset(
    {
        "id",
        "identifier",
        "ident",
        "code",
        "codigo",
        "key",
        "clave",
        "uuid",
        "guid",
        "pk",
        "fk",
        "number",
        "numero",
        "num",
        "no",
    }
)

# Backward-compatible alias used by 2D.5 header identity gate.
_IDENTIFIER_TOKENS = STRUCTURAL_TOKENS

# Declarative canonical entity aliases (2D.6). Undeclared equivalences are never invented.
ENTITY_ALIAS_GROUPS: dict[str, frozenset[str]] = {
    "customer": frozenset({"customer", "client", "cliente"}),
    "product": frozenset({"product", "article", "articulo", "item"}),
    "order": frozenset({"order", "pedido"}),
    "supplier": frozenset({"supplier", "vendor", "proveedor"}),
    "invoice": frozenset({"invoice", "factura"}),
}

_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: canonical for canonical, aliases in ENTITY_ALIAS_GROUPS.items() for alias in aliases
}

# Stems allowed when splitting glued lowercase compounds (customerid → customer + id).
_KNOWN_ENTITY_STEMS = (
    frozenset(_ALIAS_TO_CANONICAL)
    | frozenset(ENTITY_ALIAS_GROUPS)
    | frozenset(
        {
            "parent",
            "child",
            "student",
            "course",
            "sale",
            "person",
            "line",
            "row",
        }
    )
)

_SPLIT_CAMEL_LOWER_UPPER = re.compile(r"([a-z0-9])([A-Z])")
_SPLIT_CAMEL_ACRONYM = re.compile(r"([A-Z]+)([A-Z][a-z])")
_SPLIT_SEPARATORS = re.compile(r"[\s_\-/\\.:]+")


class SemanticCompatibilityStatus(StrEnum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class IdentifierSemanticSignal:
    """Normalized entity signal extracted from an identifier-like header."""

    header: str
    all_tokens: tuple[str, ...]
    structural_tokens: tuple[str, ...]
    entity_tokens: tuple[str, ...]
    canonical_entities: tuple[str, ...]
    has_entity_evidence: bool

    @property
    def canonical_entity(self) -> str | None:
        if not self.canonical_entities:
            return None
        if len(self.canonical_entities) == 1:
            return self.canonical_entities[0]
        return "+".join(self.canonical_entities)


@dataclass(frozen=True)
class SemanticCompatibilityResult:
    """Explainable comparison of child/parent reference-target semantics."""

    status: SemanticCompatibilityStatus
    child: IdentifierSemanticSignal
    parent: IdentifierSemanticSignal
    shared_entities: tuple[str, ...]
    detail: str


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _split_glued_token(token: str) -> tuple[str, ...]:
    """Split known-stem+structural compounds only; never invent stems (Paid ≠ pa)."""
    if token in STRUCTURAL_TOKENS or token in _KNOWN_ENTITY_STEMS:
        return (token,)
    # Longest structural suffix/prefix first.
    for struct in sorted(STRUCTURAL_TOKENS, key=len, reverse=True):
        if len(token) <= len(struct):
            continue
        if token.endswith(struct):
            stem = token[: -len(struct)]
            if stem in _KNOWN_ENTITY_STEMS:
                return (stem, struct)
        if token.startswith(struct):
            stem = token[len(struct) :]
            if stem in _KNOWN_ENTITY_STEMS:
                return (struct, stem)
    return (token,)


def header_tokens(effective_name: str) -> tuple[str, ...]:
    """Split a header into casefolded tokens on CamelCase and separators."""
    name = effective_name.strip()
    if not name:
        return ()
    spaced = _SPLIT_CAMEL_LOWER_UPPER.sub(r"\1 \2", name)
    spaced = _SPLIT_CAMEL_ACRONYM.sub(r"\1 \2", spaced)
    parts = _SPLIT_SEPARATORS.split(spaced)
    tokens: list[str] = []
    for part in parts:
        if not part:
            continue
        folded = _strip_accents(part).casefold()
        tokens.extend(_split_glued_token(folded))
    return tuple(tokens)


def header_suggests_identifier(effective_name: str) -> bool:
    """True when a controlled identifier token appears as a whole token."""
    tokens = header_tokens(effective_name)
    return any(token in _IDENTIFIER_TOKENS for token in tokens)


def extract_identifier_semantic_signal(effective_name: str) -> IdentifierSemanticSignal:
    """Derive normalized entity evidence from an identifier header."""
    tokens = header_tokens(effective_name)
    structural = tuple(token for token in tokens if token in STRUCTURAL_TOKENS)
    entity = tuple(token for token in tokens if token not in STRUCTURAL_TOKENS)
    canonical = tuple(sorted({_ALIAS_TO_CANONICAL.get(token, token) for token in entity}))
    return IdentifierSemanticSignal(
        header=effective_name,
        all_tokens=tokens,
        structural_tokens=structural,
        entity_tokens=entity,
        canonical_entities=canonical,
        has_entity_evidence=bool(canonical),
    )


def reference_target_semantically_compatible(
    child_signal: IdentifierSemanticSignal,
    parent_signal: IdentifierSemanticSignal,
) -> SemanticCompatibilityResult:
    """Compare reference/target entity signals (deterministic, alias-aware)."""
    if not child_signal.has_entity_evidence or not parent_signal.has_entity_evidence:
        return SemanticCompatibilityResult(
            status=SemanticCompatibilityStatus.INSUFFICIENT,
            child=child_signal,
            parent=parent_signal,
            shared_entities=(),
            detail="one or both headers lack entity tokens after structural removal",
        )
    shared = tuple(
        sorted(set(child_signal.canonical_entities) & set(parent_signal.canonical_entities))
    )
    if shared:
        return SemanticCompatibilityResult(
            status=SemanticCompatibilityStatus.COMPATIBLE,
            child=child_signal,
            parent=parent_signal,
            shared_entities=shared,
            detail=(
                f"shared canonical entit{'y' if len(shared) == 1 else 'ies'}: {', '.join(shared)}"
            ),
        )
    return SemanticCompatibilityResult(
        status=SemanticCompatibilityStatus.INCOMPATIBLE,
        child=child_signal,
        parent=parent_signal,
        shared_entities=(),
        detail=(
            f"child entities={list(child_signal.canonical_entities)} "
            f"parent entities={list(parent_signal.canonical_entities)}"
        ),
    )


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
