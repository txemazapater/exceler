"""Region detection options and limits (Phase 2B)."""

from __future__ import annotations

from dataclasses import dataclass

DETECTOR_VERSION = "2B.1"
REGIONS_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RegionDetectionOptions:
    """Tunable thresholds for HeuristicRegionDetector. Defaults match corpus contracts."""

    # Empty gap merge: gaps wider than this (in empty rows/cols) are hard separators.
    max_weak_gap_rows: int = 1
    max_weak_gap_cols: int = 1
    # Merge score in [0, 1]; components merge when score >= threshold.
    merge_score_threshold: float = 0.55
    # Column-span tolerance for title-above-table nesting (absolute columns).
    nest_column_tolerance: int = 1
    # Max vertical gap (empty rows) between title and table for nesting.
    nest_max_gap_rows: int = 2
    include_cell_coordinates: bool = True
