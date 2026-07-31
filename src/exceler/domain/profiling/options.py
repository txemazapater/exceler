"""Profiling options and version constants (Phase 2C)."""

from __future__ import annotations

from dataclasses import dataclass

PROFILER_VERSION = "2C.1"
PROFILING_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ProfilingOptions:
    include_unknown_regions: bool = True
    minimum_region_confidence: float = 0.0
    minimum_rows_for_inference: int = 2
    sample_size: int = 20
    top_values_limit: int = 20
    anomaly_sample_limit: int = 20
    max_distinct_values_tracked: int = 100_000
    max_values_profiled_per_column: int = 1_000_000
    trim_strings_for_analysis: bool = True
    case_sensitive_cardinality: bool = True
    exclude_header_rows: bool = True
    exclude_footer_rows: bool = True
    # Inference thresholds (centralized — not magic numbers in scorers)
    high_compatibility_ratio: float = 0.9
    moderate_compatibility_ratio: float = 0.6
    identifier_unique_ratio: float = 0.98
    identifier_non_null_ratio: float = 0.95
    categorical_max_distinct: int = 20
    categorical_max_distinct_ratio: float = 0.3
    sample_sufficiency_full_at: int = 30
    min_unknown_region_rows: int = 2
    min_unknown_region_cols: int = 2
