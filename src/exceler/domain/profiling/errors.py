"""Profiling domain errors (Phase 2C)."""

from __future__ import annotations


class ProfilingError(Exception):
    code: str = "PROFILING_ERROR"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ProfilingInputMismatchError(ProfilingError):
    code = "PROFILING_INPUT_MISMATCH"


class UnsupportedProfilingInputVersionError(ProfilingError):
    code = "UNSUPPORTED_PROFILING_INPUT"


class InvalidRegionContractError(ProfilingError):
    code = "INVALID_REGION_CONTRACT"
