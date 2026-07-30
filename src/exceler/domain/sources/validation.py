from __future__ import annotations

import re
from pathlib import Path, PurePath

from exceler.domain.sources.enums import AuthenticationType, SourceType
from exceler.domain.sources.errors import SourceValidationError
from exceler.domain.sources.models import DiscoverySource

_GLOB_RE = re.compile(r"^[^\x00]+$")


def validate_glob_patterns(patterns: list[str], *, field_name: str) -> None:
    if len(patterns) > 100:
        raise SourceValidationError(
            f"{field_name} exceeds maximum of 100 patterns",
            code="too_many_patterns",
        )
    for pattern in patterns:
        if not pattern or not pattern.strip():
            raise SourceValidationError(
                f"{field_name} contains an empty pattern",
                code="invalid_pattern",
            )
        if not _GLOB_RE.match(pattern):
            raise SourceValidationError(
                f"Invalid pattern in {field_name}: {pattern!r}",
                code="invalid_pattern",
            )


def validate_limits(source: DiscoverySource) -> None:
    if source.max_depth is not None and source.max_depth < 0:
        raise SourceValidationError("max_depth must be >= 0", code="invalid_limit")
    if source.max_files_per_run is not None and source.max_files_per_run < 1:
        raise SourceValidationError("max_files_per_run must be >= 1", code="invalid_limit")
    if source.max_file_size_bytes is not None and source.max_file_size_bytes < 1:
        raise SourceValidationError("max_file_size_bytes must be >= 1", code="invalid_limit")


def validate_source_invariants(source: DiscoverySource) -> None:
    if not source.name or not source.name.strip():
        raise SourceValidationError("name is required", code="invalid_name")
    if len(source.name) > 200:
        raise SourceValidationError("name exceeds 200 characters", code="invalid_name")
    if not source.read_only:
        raise SourceValidationError(
            "Discovery sources must be read_only=true",
            code="read_only_required",
        )
    if source.source_type != SourceType.FILESYSTEM:
        raise SourceValidationError(
            f"Unsupported source_type for phase 1: {source.source_type}",
            code="unsupported_source_type",
        )
    if (
        source.authentication_type == AuthenticationType.CREDENTIAL_REFERENCE
        and not source.credential_reference
    ):
        raise SourceValidationError(
            "credential_reference is required for authentication_type=credential_reference",
            code="credential_reference_required",
        )
    if source.credential_reference and any(
        token in source.credential_reference.lower() for token in ("password=", "secret=", "token=")
    ):
        raise SourceValidationError(
            "credential_reference must not embed secret material",
            code="secret_in_credential_reference",
        )
    validate_glob_patterns(source.include_patterns, field_name="include_patterns")
    validate_glob_patterns(source.exclude_patterns, field_name="exclude_patterns")
    validate_limits(source)

    root = source.root_location.strip()
    path = Path(root)
    if not path.is_absolute():
        raise SourceValidationError(
            "root_location must be an absolute path",
            code="root_not_absolute",
        )
    if ".." in PurePath(root).parts:
        raise SourceValidationError(
            "root_location must not contain '..'",
            code="root_path_traversal",
        )


def ensure_path_under_allowed_roots(root_location: str, allowed_roots: list[str]) -> Path:
    if not allowed_roots:
        raise SourceValidationError(
            "No allowed source roots configured",
            code="no_allowed_roots",
        )
    candidate = Path(root_location).resolve()
    for allowed in allowed_roots:
        allowed_path = Path(allowed).resolve()
        try:
            candidate.relative_to(allowed_path)
            return candidate
        except ValueError:
            continue
    raise SourceValidationError(
        f"root_location is outside allowed source roots: {root_location}",
        code="root_outside_allowed",
    )


def validate_filesystem_accessibility(
    root_location: str, allowed_roots: list[str]
) -> dict[str, object]:
    path = ensure_path_under_allowed_roots(root_location, allowed_roots)
    if not path.exists():
        raise SourceValidationError(
            f"root_location does not exist: {root_location}",
            code="root_missing",
        )
    if not path.is_dir():
        raise SourceValidationError(
            f"root_location is not a directory: {root_location}",
            code="root_not_directory",
        )
    try:
        next(path.iterdir(), None)
    except PermissionError as exc:
        raise SourceValidationError(
            f"root_location is not readable: {root_location}",
            code="root_not_readable",
        ) from exc
    return {
        "resolved_path": str(path),
        "exists": True,
        "is_directory": True,
        "readable": True,
    }
