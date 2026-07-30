from __future__ import annotations

from typing import Protocol
from uuid import UUID

from exceler.domain.sources.models import DiscoverySource


class SourceRepository(Protocol):
    def add(self, source: DiscoverySource) -> DiscoverySource: ...

    def get(self, source_id: UUID) -> DiscoverySource | None: ...

    def list(
        self,
        *,
        include_archived: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[DiscoverySource], int]: ...

    def save(self, source: DiscoverySource) -> DiscoverySource: ...

    def get_by_name(self, name: str) -> DiscoverySource | None: ...


class AuditPort(Protocol):
    def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, object] | None = None,
    ) -> None: ...
