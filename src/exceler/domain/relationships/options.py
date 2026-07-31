"""Relationship analysis options and version constants (Phase 2D)."""

from __future__ import annotations

from dataclasses import dataclass

RELATIONSHIP_ENGINE_VERSION = "2D.3"
RELATIONSHIP_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RelationshipOptions:
    max_distinct_values_tracked: int = 100_000
    max_fk_pair_comparisons: int = 5_000
    max_composite_pair_columns: int = 8
    enable_composite_triples: bool = False
    min_pk_distinct_ratio: float = 0.98
    min_pk_non_null_ratio: float = 0.95
    min_pk_score: float = 0.35
    min_fk_inclusion_ratio: float = 0.60
    min_fk_parent_distinct_ratio: float = 0.90
    min_fk_score: float = 0.35
    min_domain_compat_score: float = 0.45
    max_pk_candidates_per_region: int = 5
    max_fk_candidates: int = 50
    emit_rejected_key_candidates: bool = True
    orphan_sample_limit: int = 20
    case_sensitive_values: bool = True
    trim_values: bool = True
    exclude_header_rows: bool = True
    exclude_footer_rows: bool = True
    # Evidence / confidence weights (centralized)
    weight_distinct: float = 0.35
    weight_non_null: float = 0.25
    weight_identifier: float = 0.25
    weight_logical_type: float = 0.15
    weight_fk_parent_reference: float = 0.20
    weight_inclusion: float = 0.45
    weight_parent_unique: float = 0.25
    weight_domain_compat: float = 0.20
    weight_type_compat: float = 0.10
    weight_joint_unique: float = 0.55
    weight_parts_not_unique: float = 0.35
    truncation_penalty: float = 0.15
    orphan_penalty_factor: float = 0.5

    @property
    def max_pk_positive_weight(self) -> float:
        return (
            self.weight_distinct
            + self.weight_non_null
            + self.weight_identifier
            + self.weight_logical_type
            + self.weight_fk_parent_reference
        )

    @property
    def max_fk_positive_weight(self) -> float:
        return (
            self.weight_inclusion
            + self.weight_parent_unique
            + self.weight_domain_compat
            + self.weight_type_compat
        )

    @property
    def max_composite_positive_weight(self) -> float:
        return self.weight_joint_unique + self.weight_parts_not_unique
