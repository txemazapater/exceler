"""Profiling domain package (Phase 2C)."""

from __future__ import annotations

from exceler.domain.profiling.enums import (
    AnomalySeverity,
    AnomalyType,
    LogicalValueType,
    ProfilingStatus,
    StatisticExactness,
)
from exceler.domain.profiling.errors import (
    InvalidRegionContractError,
    ProfilingError,
    ProfilingInputMismatchError,
    UnsupportedProfilingInputVersionError,
)
from exceler.domain.profiling.models import (
    CategoricalAnalysis,
    ColumnAnomaly,
    ColumnProfile,
    ColumnStatistics,
    IdentifierAnalysis,
    KindCount,
    LogicalTypeInference,
    ProfilingEvidenceItem,
    ProfilingResult,
    RegionProfile,
    SampleValue,
    SheetProfiles,
    TopValue,
    TypeCandidate,
)
from exceler.domain.profiling.options import (
    PROFILER_VERSION,
    PROFILING_SCHEMA_VERSION,
    ProfilingOptions,
)

__all__ = [
    "AnomalySeverity",
    "AnomalyType",
    "CategoricalAnalysis",
    "ColumnAnomaly",
    "ColumnProfile",
    "ColumnStatistics",
    "IdentifierAnalysis",
    "InvalidRegionContractError",
    "KindCount",
    "LogicalTypeInference",
    "LogicalValueType",
    "PROFILER_VERSION",
    "PROFILING_SCHEMA_VERSION",
    "ProfilingError",
    "ProfilingEvidenceItem",
    "ProfilingInputMismatchError",
    "ProfilingOptions",
    "ProfilingResult",
    "ProfilingStatus",
    "RegionProfile",
    "SampleValue",
    "SheetProfiles",
    "StatisticExactness",
    "TopValue",
    "TypeCandidate",
    "UnsupportedProfilingInputVersionError",
]
