"""Relationship analyzer ports (Phase 2D)."""

from __future__ import annotations

from typing import Protocol

from exceler.domain.profiling.models import ProfilingResult
from exceler.domain.regions.models import RegionDetectionResult
from exceler.domain.relationships.models import RelationshipAnalysisResult
from exceler.domain.relationships.options import RelationshipOptions
from exceler.domain.workbook.models import WorkbookInspection


class RelationshipAnalyzer(Protocol):
    def analyze(
        self,
        inspection: WorkbookInspection,
        regions: RegionDetectionResult,
        profiling: ProfilingResult,
        options: RelationshipOptions | None = None,
    ) -> RelationshipAnalysisResult: ...
