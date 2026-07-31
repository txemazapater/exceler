"""Serialize ProfilingResult for CLI/JSON contracts."""

from __future__ import annotations

from typing import Any

from exceler.domain.profiling.models import ProfilingResult


def profile_to_dict(result: ProfilingResult) -> dict[str, Any]:
    return result.to_dict()
