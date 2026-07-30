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
    issues_to_items,
    source_from_create,
    source_to_read,
)
from exceler.domain.sources.errors import (
    SourceConflictError,
    SourceNotFoundError,
    SourceValidationError,
)
from exceler.domain.sources.models import DiscoverySource
from exceler.domain.sources.validation import (
    ValidationIssue,
    probe_filesystem_accessibility,
    validate_source_configuration,
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
        validate_source_configuration(source, allowed_source_roots=self._allowed_roots)
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
        return source_to_read(self._require(source_id))

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
        changes = payload.model_dump(exclude_unset=True)
        source.reconfigure(changes)
        validate_source_configuration(source, allowed_source_roots=self._allowed_roots)
        conflict = self._repository.get_by_name(source.name)
        if conflict and conflict.id != source.id and not conflict.is_archived:
            raise SourceConflictError(f"Source name already exists: {source.name}")
        saved = self._repository.save(source)
        self._audit.record(
            action="source.updated",
            entity_type="DiscoverySource",
            entity_id=str(saved.id),
            details={"fields": sorted(changes.keys())},
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
        config_errors: list[ValidationIssue] = []
        try:
            validate_source_configuration(source, allowed_source_roots=self._allowed_roots)
            configuration_valid = True
        except SourceValidationError as exc:
            configuration_valid = False
            config_errors.append(ValidationIssue(code=exc.code, message=exc.message))

        if configuration_valid:
            report = probe_filesystem_accessibility(source.root_location, self._allowed_roots)
            accessible = report.accessible
            checks = dict(report.checks)
            errors = list(report.errors)
            # probe also re-checks config; trust the dedicated config pass above
            configuration_valid = configuration_valid and report.configuration_valid
            if not report.configuration_valid:
                errors = report.errors
        else:
            accessible = False
            checks = {
                "path_resolved": False,
                "exists": False,
                "is_directory": False,
                "readable": False,
                "within_allowed_roots": False,
            }
            errors = config_errors

        checks["read_only"] = source.read_only
        valid = configuration_valid and accessible
        result = SourceValidationResult(
            valid=valid,
            configuration_valid=configuration_valid,
            accessible=accessible,
            checks=checks,
            errors=issues_to_items(errors),
            message=(
                "Source is configured and currently accessible"
                if valid
                else "Source validation completed with findings"
            ),
        )
        self._audit.record(
            action="source.validated",
            entity_type="DiscoverySource",
            entity_id=str(source.id),
            details={
                "valid": result.valid,
                "configuration_valid": result.configuration_valid,
                "accessible": result.accessible,
                "error_codes": [item.code for item in result.errors],
            },
        )
        return result

    def _require(self, source_id: UUID) -> DiscoverySource:
        source = self._repository.get(source_id)
        if source is None:
            raise SourceNotFoundError(str(source_id))
        return source
