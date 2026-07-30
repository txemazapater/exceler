"""Region detection domain package (Phase 2B)."""

from __future__ import annotations

from exceler.domain.regions.models import (
    BoundingBox,
    LogicalRegion,
    RegionDetectionResult,
    RegionEvidenceItem,
    RegionStatistics,
    RegionStyleProfile,
    RegionType,
    SheetRegions,
)
from exceler.domain.regions.options import (
    DETECTOR_VERSION,
    REGIONS_SCHEMA_VERSION,
    RegionDetectionOptions,
)

__all__ = [
    "BoundingBox",
    "DETECTOR_VERSION",
    "LogicalRegion",
    "REGIONS_SCHEMA_VERSION",
    "RegionDetectionOptions",
    "RegionDetectionResult",
    "RegionEvidenceItem",
    "RegionStatistics",
    "RegionStyleProfile",
    "RegionType",
    "SheetRegions",
]
