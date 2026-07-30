from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from exceler.domain.sources.enums import AuthenticationType, ScanPolicy, SourceType
from exceler.domain.sources.models import DiscoverySource


class Base(DeclarativeBase):
    pass


class DiscoverySourceRow(Base):
    __tablename__ = "discovery_sources"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    endpoint: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    root_location: Mapped[str] = mapped_column(String(2048), nullable=False)
    authentication_type: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_reference: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    read_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    recursive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    include_patterns: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    exclude_patterns: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    max_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_files_per_run: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scan_policy: Mapped[str] = mapped_column(String(64), nullable=False)
    connector_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


def row_to_domain(row: DiscoverySourceRow) -> DiscoverySource:
    return DiscoverySource(
        id=row.id,
        name=row.name,
        source_type=SourceType(row.source_type),
        endpoint=row.endpoint,
        root_location=row.root_location,
        authentication_type=AuthenticationType(row.authentication_type),
        credential_reference=row.credential_reference,
        enabled=row.enabled,
        read_only=row.read_only,
        recursive=row.recursive,
        include_patterns=list(row.include_patterns or []),
        exclude_patterns=list(row.exclude_patterns or []),
        max_depth=row.max_depth,
        max_files_per_run=row.max_files_per_run,
        max_file_size_bytes=row.max_file_size_bytes,
        scan_policy=ScanPolicy(row.scan_policy),
        connector_settings=dict(row.connector_settings or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
        archived_at=row.archived_at,
        last_successful_run_at=row.last_successful_run_at,
        last_error=row.last_error,
    )


def sync_row(row: DiscoverySourceRow, source: DiscoverySource) -> None:
    row.id = source.id
    row.name = source.name
    row.source_type = source.source_type.value
    row.endpoint = source.endpoint
    row.root_location = source.root_location
    row.authentication_type = source.authentication_type.value
    row.credential_reference = source.credential_reference
    row.enabled = source.enabled
    row.read_only = source.read_only
    row.recursive = source.recursive
    row.include_patterns = list(source.include_patterns)
    row.exclude_patterns = list(source.exclude_patterns)
    row.max_depth = source.max_depth
    row.max_files_per_run = source.max_files_per_run
    row.max_file_size_bytes = source.max_file_size_bytes
    row.scan_policy = source.scan_policy.value
    row.connector_settings = dict(source.connector_settings)
    row.created_at = source.created_at
    row.updated_at = source.updated_at
    row.archived_at = source.archived_at
    row.last_successful_run_at = source.last_successful_run_at
    row.last_error = source.last_error


class SqlAlchemySourceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, source: DiscoverySource) -> DiscoverySource:
        row = DiscoverySourceRow(
            id=source.id,
            name=source.name,
            source_type=source.source_type.value,
            endpoint=source.endpoint,
            root_location=source.root_location,
            authentication_type=source.authentication_type.value,
            credential_reference=source.credential_reference,
            enabled=source.enabled,
            read_only=source.read_only,
            recursive=source.recursive,
            include_patterns=list(source.include_patterns),
            exclude_patterns=list(source.exclude_patterns),
            max_depth=source.max_depth,
            max_files_per_run=source.max_files_per_run,
            max_file_size_bytes=source.max_file_size_bytes,
            scan_policy=source.scan_policy.value,
            connector_settings=dict(source.connector_settings),
            created_at=source.created_at,
            updated_at=source.updated_at,
            archived_at=source.archived_at,
            last_successful_run_at=source.last_successful_run_at,
            last_error=source.last_error,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row_to_domain(row)

    def get(self, source_id: UUID) -> DiscoverySource | None:
        row = self._session.get(DiscoverySourceRow, source_id)
        return row_to_domain(row) if row else None

    def get_by_name(self, name: str) -> DiscoverySource | None:
        active = self._session.scalar(
            select(DiscoverySourceRow).where(
                DiscoverySourceRow.name == name,
                DiscoverySourceRow.archived_at.is_(None),
            )
        )
        if active:
            return row_to_domain(active)
        row = self._session.scalar(
            select(DiscoverySourceRow)
            .where(DiscoverySourceRow.name == name)
            .order_by(DiscoverySourceRow.updated_at.desc())
        )
        return row_to_domain(row) if row else None

    def list(
        self,
        *,
        include_archived: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[DiscoverySource], int]:
        stmt = select(DiscoverySourceRow)
        count_stmt = select(func.count()).select_from(DiscoverySourceRow)
        if not include_archived:
            stmt = stmt.where(DiscoverySourceRow.archived_at.is_(None))
            count_stmt = count_stmt.where(DiscoverySourceRow.archived_at.is_(None))
        total = int(self._session.scalar(count_stmt) or 0)
        rows = self._session.scalars(
            stmt.order_by(DiscoverySourceRow.name).offset(offset).limit(limit)
        ).all()
        return [row_to_domain(row) for row in rows], total

    def save(self, source: DiscoverySource) -> DiscoverySource:
        row = self._session.get(DiscoverySourceRow, source.id)
        if row is None:
            return self.add(source)
        sync_row(row, source)
        self._session.commit()
        self._session.refresh(row)
        return row_to_domain(row)


class SqlAlchemyAuditLogger:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, object] | None = None,
    ) -> None:
        self._session.add(
            AuditEventRow(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=dict(details or {}),
            )
        )
        self._session.commit()
