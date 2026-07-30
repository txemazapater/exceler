"""Region detection application package (Phase 2B)."""

from __future__ import annotations

from exceler.application.regions.heuristic_detector import HeuristicRegionDetector
from exceler.application.regions.ports import RegionDetector
from exceler.application.regions.serialization import regions_to_dict

__all__ = ["HeuristicRegionDetector", "RegionDetector", "regions_to_dict"]
