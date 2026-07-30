from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from exceler.domain.sources.enums import AuthenticationType, ScanPolicy, SourceType
from exceler.domain.sources.errors import SourceConflictError, SourceValidationError


def utc_now() -> datetime:
    return datetime.now(UTC)


_RECONFIGURABLE_FIELDS = frozenset(
    {
        "name",
        "endpoint",
        "root_location",
        "authentication_type",
        "credential_reference",
        "recursive",
        "include_patterns",
        "exclude_patterns",
        "max_depth",
        "max_files_per_run",
        "max_file_size_bytes",
        "scan_policy",
        "connector_settings",
        "read_only",
    }
)

_PROTECTED_FIELDS = frozenset(
    {
        "id",
        "created_at",
        "updated_at",
        "archived_at",
        "last_successful_run_at",
        "last_error",
        "enabled",
        "source_type",
    }
)


@dataclass
class DiscoverySource:
    name: str
    source_type: SourceType
    root_location: str
    id: UUID = field(default_factory=uuid4)
    endpoint: str | None = None
    authentication_type: AuthenticationType = AuthenticationType.HOST_MOUNT
    credential_reference: str | None = None
    enabled: bool = True
    read_only: bool = True
    recursive: bool = True
    include_patterns: list[str] = field(default_factory=lambda: ["*.xlsx", "*.xlsm", "*.xls"])
    exclude_patterns: list[str] = field(default_factory=list)
    max_depth: int | None = 16
    max_files_per_run: int | None = 10_000
    max_file_size_bytes: int | None = 100 * 1024 * 1024
    scan_policy: ScanPolicy = ScanPolicy.MANUAL
    connector_settings: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    archived_at: datetime | None = None
    last_successful_run_at: datetime | None = None
    last_error: str | None = None

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    def touch(self) -> None:
        self.updated_at = utc_now()

    def archive(self) -> None:
        if self.is_archived:
            return
        self.archived_at = utc_now()
        self.enabled = False
        self.touch()

    def set_enabled(self, enabled: bool) -> None:
        if self.is_archived:
            raise SourceConflictError("Cannot change status of an archived source")
        self.enabled = enabled
        self.touch()

    def reconfigure(self, changes: dict[str, Any]) -> None:
        """Apply allowed configuration changes while protecting identity/audit fields."""
        if self.is_archived:
            raise SourceConflictError("Cannot update an archived source")

        unknown = set(changes) - _RECONFIGURABLE_FIELDS
        protected_attempt = set(changes) & _PROTECTED_FIELDS
        if protected_attempt:
            raise SourceValidationError(
                f"Cannot modify protected fields: {sorted(protected_attempt)}",
                code="protected_field",
            )
        if unknown:
            raise SourceValidationError(
                f"Unknown reconfigure fields: {sorted(unknown)}",
                code="unknown_field",
            )

        for key, value in changes.items():
            if key == "name" and isinstance(value, str):
                value = value.strip()
            if key in {"include_patterns", "exclude_patterns"} and value is not None:
                value = list(value)
            if key == "connector_settings" and value is not None:
                value = dict(value)
            setattr(self, key, value)

        self.touch()
