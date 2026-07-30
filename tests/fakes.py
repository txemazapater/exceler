from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from uuid import UUID

from exceler.domain.sources.models import DiscoverySource


@dataclass
class InMemorySourceRepository:
    _items: dict[UUID, DiscoverySource] = field(default_factory=dict)

    def add(self, source: DiscoverySource) -> DiscoverySource:
        stored = deepcopy(source)
        self._items[stored.id] = stored
        return deepcopy(stored)

    def get(self, source_id: UUID) -> DiscoverySource | None:
        source = self._items.get(source_id)
        return deepcopy(source) if source else None

    def list(
        self,
        *,
        include_archived: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[DiscoverySource], int]:
        values = list(self._items.values())
        if not include_archived:
            values = [item for item in values if not item.is_archived]
        values.sort(key=lambda item: item.name)
        total = len(values)
        page = values[offset : offset + limit]
        return [deepcopy(item) for item in page], total

    def save(self, source: DiscoverySource) -> DiscoverySource:
        self._items[source.id] = deepcopy(source)
        return deepcopy(source)

    def get_by_name(self, name: str) -> DiscoverySource | None:
        active = [
            item for item in self._items.values() if item.name == name and not item.is_archived
        ]
        if active:
            return deepcopy(active[0])
        matches = [item for item in self._items.values() if item.name == name]
        if not matches:
            return None
        matches.sort(key=lambda item: item.updated_at, reverse=True)
        return deepcopy(matches[0])


@dataclass
class RecordingAuditLogger:
    events: list[dict[str, object]] = field(default_factory=list)

    def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, object] | None = None,
    ) -> None:
        self.events.append(
            {
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "details": dict(details or {}),
            }
        )
