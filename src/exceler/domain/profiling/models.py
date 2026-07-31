"""Profiling domain models (Phase 2C)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from exceler.domain.profiling.enums import (
    AnomalySeverity,
    AnomalyType,
    LogicalValueType,
    ProfilingStatus,
    StatisticExactness,
)
from exceler.domain.regions.models import BoundingBox, RegionType
from exceler.domain.workbook.enums import CellValueKind


def _dec(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


@dataclass(frozen=True)
class ProfilingEvidenceItem:
    code: str
    weight: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "weight": self.weight,
            "message": self.message,
        }
        if self.details:
            payload["details"] = dict(self.details)
        return payload


@dataclass(frozen=True)
class KindCount:
    count: int
    ratio: float

    def to_dict(self) -> dict[str, Any]:
        return {"count": self.count, "ratio": self.ratio}


@dataclass(frozen=True)
class TypeCandidate:
    type: LogicalValueType
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type.value, "confidence": self.confidence}


@dataclass(frozen=True)
class LogicalTypeInference:
    selected_type: LogicalValueType
    confidence: float
    alternatives: tuple[TypeCandidate, ...]
    evidence: tuple[ProfilingEvidenceItem, ...]
    incompatible_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_type": self.selected_type.value,
            "confidence": self.confidence,
            "alternatives": [item.to_dict() for item in self.alternatives],
            "evidence": [item.to_dict() for item in self.evidence],
            "incompatible_count": self.incompatible_count,
        }


@dataclass(frozen=True)
class IdentifierAnalysis:
    is_candidate: bool
    confidence: float
    unique_ratio: float
    non_null_ratio: float
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_candidate": self.is_candidate,
            "confidence": self.confidence,
            "unique_ratio": self.unique_ratio,
            "non_null_ratio": self.non_null_ratio,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class TopValue:
    value: str
    count: int
    ratio: float

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "count": self.count, "ratio": self.ratio}


@dataclass(frozen=True)
class CategoricalAnalysis:
    is_categorical_candidate: bool
    confidence: float
    distinct_count: int
    top_values: tuple[TopValue, ...]
    coverage_of_top_values: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_categorical_candidate": self.is_categorical_candidate,
            "confidence": self.confidence,
            "distinct_count": self.distinct_count,
            "top_values": [item.to_dict() for item in self.top_values],
            "coverage_of_top_values": self.coverage_of_top_values,
        }


@dataclass(frozen=True)
class ColumnAnomaly:
    coordinate: str | None
    original_value: str | None
    anomaly_type: AnomalyType
    message: str
    expected_type: LogicalValueType | None
    severity: AnomalySeverity

    def to_dict(self) -> dict[str, Any]:
        return {
            "coordinate": self.coordinate,
            "original_value": self.original_value,
            "anomaly_type": self.anomaly_type.value,
            "message": self.message,
            "expected_type": self.expected_type.value if self.expected_type else None,
            "severity": self.severity.value,
        }


@dataclass(frozen=True)
class SampleValue:
    coordinate: str | None
    original: str | None
    kind: CellValueKind | None
    role: str  # first | middle | last | anomaly | top

    def to_dict(self) -> dict[str, Any]:
        return {
            "coordinate": self.coordinate,
            "original": self.original,
            "kind": self.kind.value if self.kind else None,
            "role": self.role,
        }


@dataclass(frozen=True)
class TextStatistics:
    min_length: int | None
    max_length: int | None
    average_length: float | None
    median_length: float | None
    empty_string_count: int
    whitespace_only_count: int
    multiline_count: int
    dominant_patterns: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_length": self.min_length,
            "max_length": self.max_length,
            "average_length": self.average_length,
            "median_length": self.median_length,
            "empty_string_count": self.empty_string_count,
            "whitespace_only_count": self.whitespace_only_count,
            "multiline_count": self.multiline_count,
            "dominant_patterns": list(self.dominant_patterns),
        }


@dataclass(frozen=True)
class NumericStatistics:
    minimum: Decimal | None
    maximum: Decimal | None
    mean: Decimal | None
    median: Decimal | None
    standard_deviation: Decimal | None
    zero_count: int
    negative_count: int
    positive_count: int
    excluded_incompatible_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "minimum": _dec(self.minimum),
            "maximum": _dec(self.maximum),
            "mean": _dec(self.mean),
            "median": _dec(self.median),
            "standard_deviation": _dec(self.standard_deviation),
            "zero_count": self.zero_count,
            "negative_count": self.negative_count,
            "positive_count": self.positive_count,
            "excluded_incompatible_count": self.excluded_incompatible_count,
        }


@dataclass(frozen=True)
class TemporalStatistics:
    minimum: str | None
    maximum: str | None
    range_label: str | None
    distinct_count: int
    chronological_order_ratio: float | None
    dominant_pattern: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "minimum": self.minimum,
            "maximum": self.maximum,
            "range": self.range_label,
            "distinct_count": self.distinct_count,
            "chronological_order_ratio": self.chronological_order_ratio,
            "dominant_pattern": self.dominant_pattern,
        }


@dataclass(frozen=True)
class ColumnStatistics:
    total_row_count: int
    observed_count: int
    content_count: int
    null_count: int
    blank_string_count: int
    whitespace_only_count: int
    unobserved_count: int
    formula_count: int
    error_count: int
    distinct_count: int
    distinct_ratio: float
    duplicate_count: int
    unique_count: int
    unique_ratio: float
    exactness: StatisticExactness
    text: TextStatistics | None = None
    numeric: NumericStatistics | None = None
    temporal: TemporalStatistics | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "total_row_count": self.total_row_count,
            "observed_count": self.observed_count,
            "content_count": self.content_count,
            "null_count": self.null_count,
            "blank_string_count": self.blank_string_count,
            "whitespace_only_count": self.whitespace_only_count,
            "unobserved_count": self.unobserved_count,
            "formula_count": self.formula_count,
            "error_count": self.error_count,
            "distinct_count": self.distinct_count,
            "distinct_ratio": self.distinct_ratio,
            "duplicate_count": self.duplicate_count,
            "unique_count": self.unique_count,
            "unique_ratio": self.unique_ratio,
            "exactness": self.exactness.value,
        }
        if self.text is not None:
            payload["text"] = self.text.to_dict()
        if self.numeric is not None:
            payload["numeric"] = self.numeric.to_dict()
        if self.temporal is not None:
            payload["temporal"] = self.temporal.to_dict()
        return payload


@dataclass(frozen=True)
class ColumnProfile:
    id: str
    region_id: str
    sheet_name: str
    column_index: int
    column_letter: str
    header_values: tuple[str, ...]
    effective_name: str
    statistics: ColumnStatistics
    physical_type_distribution: dict[str, KindCount]
    logical_type_inference: LogicalTypeInference
    identifier_analysis: IdentifierAnalysis
    categorical_analysis: CategoricalAnalysis
    anomalies: tuple[ColumnAnomaly, ...]
    sample: tuple[SampleValue, ...]
    evidence: tuple[ProfilingEvidenceItem, ...]
    footer_values: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "region_id": self.region_id,
            "sheet_name": self.sheet_name,
            "column_index": self.column_index,
            "column_letter": self.column_letter,
            "header_values": list(self.header_values),
            "effective_name": self.effective_name,
            "footer_values": list(self.footer_values),
            "statistics": self.statistics.to_dict(),
            "physical_type_distribution": {
                key: value.to_dict() for key, value in self.physical_type_distribution.items()
            },
            "logical_type_inference": self.logical_type_inference.to_dict(),
            "identifier_analysis": self.identifier_analysis.to_dict(),
            "categorical_analysis": self.categorical_analysis.to_dict(),
            "anomalies": [item.to_dict() for item in self.anomalies],
            "sample": [item.to_dict() for item in self.sample],
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class RegionProfile:
    region_id: str
    region_type: RegionType
    bounding_box: BoundingBox
    profiling_status: ProfilingStatus
    row_count: int
    data_row_count: int
    columns: tuple[ColumnProfile, ...]
    warnings: tuple[str, ...] = ()
    evidence: tuple[ProfilingEvidenceItem, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "region_type": self.region_type.value,
            "bounding_box": self.bounding_box.to_dict(),
            "profiling_status": self.profiling_status.value,
            "row_count": self.row_count,
            "data_row_count": self.data_row_count,
            "columns": [col.to_dict() for col in self.columns],
            "warnings": list(self.warnings),
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class SheetProfiles:
    sheet_name: str
    sheet_index: int
    region_profiles: tuple[RegionProfile, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sheet_name": self.sheet_name,
            "sheet_index": self.sheet_index,
            "region_profiles": [item.to_dict() for item in self.region_profiles],
        }


@dataclass(frozen=True)
class ProfilingResult:
    workbook_hash: str
    inspector_version: str
    region_detector_version: str
    regions_schema_version: int
    profiler_version: str
    profiling_schema_version: int
    sheets: tuple[SheetProfiles, ...]
    warnings: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "profiling_schema_version": self.profiling_schema_version,
            "workbook_hash": self.workbook_hash,
            "inspector_version": self.inspector_version,
            "region_detector_version": self.region_detector_version,
            "regions_schema_version": self.regions_schema_version,
            "profiler_version": self.profiler_version,
            "sheets": [sheet.to_dict() for sheet in self.sheets],
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }
