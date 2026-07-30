from __future__ import annotations

from enum import StrEnum


class SourceType(StrEnum):
    FILESYSTEM = "filesystem"


class AuthenticationType(StrEnum):
    NONE = "none"
    HOST_MOUNT = "host_mount"
    CREDENTIAL_REFERENCE = "credential_reference"


class ScanPolicy(StrEnum):
    MANUAL = "manual"
    ON_DEMAND = "on_demand"
