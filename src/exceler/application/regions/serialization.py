"""Serialize RegionDetectionResult for CLI/JSON contracts."""

from __future__ import annotations

from typing import Any

from exceler.domain.regions.models import RegionDetectionResult


def regions_to_dict(result: RegionDetectionResult) -> dict[str, Any]:
    return result.to_dict()
