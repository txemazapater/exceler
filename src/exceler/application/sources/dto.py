from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from exceler.domain.sources.enums import AuthenticationType, ScanPolicy, SourceType
from exceler.domain.sources.models import DiscoverySource


class SourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    source_type: SourceType = SourceType.FILESYSTEM
    endpoint: str | None = None
    root_location: str
    authentication_type: AuthenticationType = AuthenticationType.HOST_MOUNT
    credential_reference: str | None = None
    enabled: bool = True
    read_only: bool = True
    recursive: bool = True
    include_patterns: list[str] = Field(default_factory=lambda: ["*.xlsx", "*.xlsm", "*.xls"])
    exclude_patterns: list[str] = Field(default_factory=list)
    max_depth: int | None = 16
    max_files_per_run: int | None = 10_000
    max_file_size_bytes: int | None = 100 * 1024 * 1024
    scan_policy: ScanPolicy = ScanPolicy.MANUAL
    connector_settings: dict[str, Any] = Field(default_factory=dict)


class SourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    endpoint: str | None = None
    root_location: str | None = None
    authentication_type: AuthenticationType | None = None
    credential_reference: str | None = None
    recursive: bool | None = None
    include_patterns: list[str] | None = None
    exclude_patterns: list[str] | None = None
    max_depth: int | None = None
    max_files_per_run: int | None = None
    max_file_size_bytes: int | None = None
    scan_policy: ScanPolicy | None = None
    connector_settings: dict[str, Any] | None = None
    read_only: bool | None = None


class SourceStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    source_type: SourceType
    endpoint: str | None
    root_location: str
    authentication_type: AuthenticationType
    credential_reference: str | None
    enabled: bool
    read_only: bool
    recursive: bool
    include_patterns: list[str]
    exclude_patterns: list[str]
    max_depth: int | None
    max_files_per_run: int | None
    max_file_size_bytes: int | None
    scan_policy: ScanPolicy
    connector_settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    last_successful_run_at: datetime | None
    last_error: str | None
    is_archived: bool


class SourceList(BaseModel):
    items: list[SourceRead]
    total: int
    offset: int
    limit: int


class SourceValidationResult(BaseModel):
    valid: bool
    checks: dict[str, object]
    message: str


def source_from_create(payload: SourceCreate) -> DiscoverySource:
    return DiscoverySource(
        name=payload.name.strip(),
        source_type=payload.source_type,
        endpoint=payload.endpoint,
        root_location=payload.root_location,
        authentication_type=payload.authentication_type,
        credential_reference=payload.credential_reference,
        enabled=payload.enabled,
        read_only=payload.read_only,
        recursive=payload.recursive,
        include_patterns=list(payload.include_patterns),
        exclude_patterns=list(payload.exclude_patterns),
        max_depth=payload.max_depth,
        max_files_per_run=payload.max_files_per_run,
        max_file_size_bytes=payload.max_file_size_bytes,
        scan_policy=payload.scan_policy,
        connector_settings=dict(payload.connector_settings),
    )


def source_to_read(source: DiscoverySource) -> SourceRead:
    data = asdict(source)
    data["is_archived"] = source.is_archived
    return SourceRead.model_validate(data)
