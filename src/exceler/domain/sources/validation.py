from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from urllib.parse import urlparse

from exceler.domain.sources.enums import AuthenticationType, SourceType
from exceler.domain.sources.errors import SourceValidationError
from exceler.domain.sources.models import DiscoverySource

_GLOB_RE = re.compile(r"^[^\x00]+$")
_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ALLOWED_CREDENTIAL_SCHEMES = frozenset({"env", "file"})
_FUTURE_CREDENTIAL_SCHEMES = frozenset({"vault", "keyring", "secret-manager"})


@dataclass
class ValidationIssue:
    code: str
    message: str


@dataclass
class AccessibilityReport:
    configuration_valid: bool
    accessible: bool
    checks: dict[str, object] = field(default_factory=dict)
    errors: list[ValidationIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.configuration_valid and self.accessible


def validate_credential_reference(reference: str | None, *, required: bool = False) -> None:
    if reference is None or reference == "":
        if required:
            raise SourceValidationError(
                "credential_reference is required",
                code="credential_reference_required",
            )
        return

    parsed = urlparse(reference)
    scheme = parsed.scheme.lower()
    if scheme in _FUTURE_CREDENTIAL_SCHEMES:
        raise SourceValidationError(
            f"credential_reference scheme '{scheme}://' is reserved for a future phase",
            code="credential_scheme_not_supported",
        )
    if scheme not in _ALLOWED_CREDENTIAL_SCHEMES:
        raise SourceValidationError(
            "credential_reference must use env:// or file:// (bare secrets are rejected)",
            code="invalid_credential_reference",
        )

    if scheme == "env":
        name = (parsed.netloc or parsed.path.lstrip("/")).strip()
        if not name or not _ENV_NAME_RE.match(name) or parsed.query or parsed.fragment:
            raise SourceValidationError(
                "credential_reference env:// must be env://VARIABLE_NAME",
                code="invalid_credential_reference",
            )
        return

    if not reference.startswith("file:///"):
        raise SourceValidationError(
            "credential_reference file:// must be an absolute file:/// path",
            code="invalid_credential_reference",
        )
    path = parsed.path
    if not path or path == "/":
        raise SourceValidationError(
            "credential_reference file:// path is empty",
            code="invalid_credential_reference",
        )


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


def path_within_allowed_roots(root_location: str, allowed_roots: list[str]) -> bool:
    if not allowed_roots:
        return False
    try:
        candidate = Path(root_location).resolve(strict=False)
    except OSError:
        candidate = Path(root_location)
    for allowed in allowed_roots:
        try:
            allowed_path = Path(allowed).resolve(strict=False)
            candidate.relative_to(allowed_path)
            return True
        except (ValueError, OSError):
            # Lexical fallback for paths that do not exist yet.
            cand_parts = PurePath(root_location).parts
            allowed_parts = PurePath(allowed).parts
            if (
                len(cand_parts) >= len(allowed_parts)
                and cand_parts[: len(allowed_parts)] == allowed_parts
            ):
                return True
            continue
    return False


def validate_source_configuration(
    source: DiscoverySource,
    *,
    allowed_source_roots: list[str] | None = None,
) -> None:
    """Validate configuration only — does not require current accessibility."""
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
    validate_credential_reference(
        source.credential_reference,
        required=source.authentication_type == AuthenticationType.CREDENTIAL_REFERENCE,
    )
    if source.credential_reference:
        validate_credential_reference(source.credential_reference, required=False)

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

    if allowed_source_roots is not None:
        if not allowed_source_roots:
            raise SourceValidationError(
                "No allowed source roots configured",
                code="no_allowed_roots",
            )
        if not path_within_allowed_roots(root, allowed_source_roots):
            raise SourceValidationError(
                f"root_location is outside allowed source roots: {root}",
                code="root_outside_allowed",
            )


def validate_source_invariants(source: DiscoverySource) -> None:
    validate_source_configuration(source)


def probe_filesystem_accessibility(
    root_location: str, allowed_roots: list[str]
) -> AccessibilityReport:
    """Probe current accessibility. Expected failures become structured errors."""
    checks: dict[str, object] = {
        "path_resolved": False,
        "exists": False,
        "is_directory": False,
        "readable": False,
        "within_allowed_roots": False,
    }
    errors: list[ValidationIssue] = []

    within = path_within_allowed_roots(root_location, allowed_roots)
    checks["within_allowed_roots"] = within
    if not within:
        errors.append(
            ValidationIssue(
                code="root_outside_allowed",
                message="The configured source path is outside allowed source roots",
            )
        )
        return AccessibilityReport(
            configuration_valid=True,
            accessible=False,
            checks=checks,
            errors=errors,
        )

    try:
        path = Path(root_location).resolve(strict=False)
        checks["path_resolved"] = True
        checks["resolved_path"] = str(path)
    except OSError as exc:
        errors.append(
            ValidationIssue(
                code="root_unresolvable",
                message=f"The configured source path could not be resolved: {exc}",
            )
        )
        return AccessibilityReport(
            configuration_valid=True,
            accessible=False,
            checks=checks,
            errors=errors,
        )

    try:
        exists = path.exists()
    except OSError as exc:
        errors.append(
            ValidationIssue(
                code="root_unavailable",
                message=f"The configured source path is temporarily unavailable: {exc}",
            )
        )
        return AccessibilityReport(
            configuration_valid=True,
            accessible=False,
            checks=checks,
            errors=errors,
        )

    checks["exists"] = exists
    if not exists:
        errors.append(
            ValidationIssue(
                code="root_missing",
                message="The configured source path does not currently exist",
            )
        )
        return AccessibilityReport(
            configuration_valid=True,
            accessible=False,
            checks=checks,
            errors=errors,
        )

    is_dir = path.is_dir()
    checks["is_directory"] = is_dir
    if not is_dir:
        errors.append(
            ValidationIssue(
                code="root_not_directory",
                message="The configured source path exists but is not a directory",
            )
        )
        return AccessibilityReport(
            configuration_valid=True,
            accessible=False,
            checks=checks,
            errors=errors,
        )

    try:
        next(path.iterdir(), None)
        checks["readable"] = True
    except PermissionError:
        errors.append(
            ValidationIssue(
                code="root_not_readable",
                message="The configured source path is not readable with current permissions",
            )
        )
        return AccessibilityReport(
            configuration_valid=True,
            accessible=False,
            checks=checks,
            errors=errors,
        )
    except OSError as exc:
        errors.append(
            ValidationIssue(
                code="root_unavailable",
                message=f"The configured source path could not be listed: {exc}",
            )
        )
        return AccessibilityReport(
            configuration_valid=True,
            accessible=False,
            checks=checks,
            errors=errors,
        )

    return AccessibilityReport(
        configuration_valid=True,
        accessible=True,
        checks=checks,
        errors=errors,
    )
