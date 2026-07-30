"""Region detection ports (Phase 2B)."""

from __future__ import annotations

from typing import Protocol

from exceler.domain.regions.models import RegionDetectionResult
from exceler.domain.regions.options import RegionDetectionOptions
from exceler.domain.workbook.models import WorkbookInspection


class RegionDetector(Protocol):
    def detect(
        self,
        inspection: WorkbookInspection,
        options: RegionDetectionOptions | None = None,
    ) -> RegionDetectionResult: ...
