"""Profiling ports (Phase 2C)."""

from __future__ import annotations

from typing import Protocol

from exceler.domain.profiling.models import ProfilingResult
from exceler.domain.profiling.options import ProfilingOptions
from exceler.domain.regions.models import RegionDetectionResult
from exceler.domain.workbook.models import WorkbookInspection


class RegionProfiler(Protocol):
    def profile(
        self,
        inspection: WorkbookInspection,
        regions: RegionDetectionResult,
        options: ProfilingOptions | None = None,
    ) -> ProfilingResult: ...
