from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from exceler.domain.sources.enums import AuthenticationType, ScanPolicy, SourceType


def utc_now() -> datetime:
    return datetime.now(UTC)


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
        self.archived_at = utc_now()
        self.enabled = False
        self.touch()

    def set_enabled(self, enabled: bool) -> None:
        if self.is_archived:
            raise ValueError("Cannot change status of an archived source")
        self.enabled = enabled
        self.touch()
