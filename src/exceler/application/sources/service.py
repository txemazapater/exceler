from __future__ import annotations

from uuid import UUID

from exceler.application.ports import AuditPort, SourceRepository
from exceler.application.sources.dto import (
    SourceCreate,
    SourceList,
    SourceRead,
    SourceStatusUpdate,
    SourceUpdate,
    SourceValidationResult,
    source_from_create,
    source_to_read,
)
from exceler.domain.sources.errors import SourceConflictError, SourceNotFoundError
from exceler.domain.sources.models import DiscoverySource
from exceler.domain.sources.validation import (
    validate_filesystem_accessibility,
    validate_source_invariants,
)


class SourceService:
    def __init__(
        self,
        repository: SourceRepository,
        audit: AuditPort,
        *,
        allowed_source_roots: list[str],
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._allowed_roots = allowed_source_roots

    def create(self, payload: SourceCreate) -> SourceRead:
        source = source_from_create(payload)
        validate_source_invariants(source)
        validate_filesystem_accessibility(source.root_location, self._allowed_roots)
        existing = self._repository.get_by_name(source.name)
        if existing and not existing.is_archived:
            raise SourceConflictError(f"Source name already exists: {source.name}")
        saved = self._repository.add(source)
        self._audit.record(
            action="source.created",
            entity_type="DiscoverySource",
            entity_id=str(saved.id),
            details={"name": saved.name, "root_location": saved.root_location},
        )
        return source_to_read(saved)

    def get(self, source_id: UUID) -> SourceRead:
        source = self._require(source_id)
        return source_to_read(source)

    def list(
        self, *, include_archived: bool = False, offset: int = 0, limit: int = 50
    ) -> SourceList:
        items, total = self._repository.list(
            include_archived=include_archived,
            offset=offset,
            limit=limit,
        )
        return SourceList(
            items=[source_to_read(item) for item in items],
            total=total,
            offset=offset,
            limit=limit,
        )

    def update(self, source_id: UUID, payload: SourceUpdate) -> SourceRead:
        source = self._require(source_id)
        if source.is_archived:
            raise SourceConflictError("Cannot update an archived source")
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(source, key, value)
        if "name" in data and isinstance(source.name, str):
            source.name = source.name.strip()
        validate_source_invariants(source)
        validate_filesystem_accessibility(source.root_location, self._allowed_roots)
        conflict = self._repository.get_by_name(source.name)
        if conflict and conflict.id != source.id and not conflict.is_archived:
            raise SourceConflictError(f"Source name already exists: {source.name}")
        source.touch()
        saved = self._repository.save(source)
        self._audit.record(
            action="source.updated",
            entity_type="DiscoverySource",
            entity_id=str(saved.id),
            details={"fields": sorted(data.keys())},
        )
        return source_to_read(saved)

    def set_status(self, source_id: UUID, payload: SourceStatusUpdate) -> SourceRead:
        source = self._require(source_id)
        source.set_enabled(payload.enabled)
        saved = self._repository.save(source)
        self._audit.record(
            action="source.status_changed",
            entity_type="DiscoverySource",
            entity_id=str(saved.id),
            details={"enabled": saved.enabled},
        )
        return source_to_read(saved)

    def archive(self, source_id: UUID) -> SourceRead:
        source = self._require(source_id)
        if source.is_archived:
            return source_to_read(source)
        source.archive()
        saved = self._repository.save(source)
        self._audit.record(
            action="source.archived",
            entity_type="DiscoverySource",
            entity_id=str(saved.id),
            details={"name": saved.name},
        )
        return source_to_read(saved)

    def validate(self, source_id: UUID) -> SourceValidationResult:
        source = self._require(source_id)
        validate_source_invariants(source)
        checks = validate_filesystem_accessibility(source.root_location, self._allowed_roots)
        checks.update(
            {
                "read_only": source.read_only,
                "patterns_ok": True,
                "limits_ok": True,
                "within_allowed_roots": True,
            }
        )
        self._audit.record(
            action="source.validated",
            entity_type="DiscoverySource",
            entity_id=str(source.id),
            details={"valid": True},
        )
        return SourceValidationResult(
            valid=True,
            checks=checks,
            message="Source configuration is valid",
        )

    def _require(self, source_id: UUID) -> DiscoverySource:
        source = self._repository.get(source_id)
        if source is None:
            raise SourceNotFoundError(str(source_id))
        return source
