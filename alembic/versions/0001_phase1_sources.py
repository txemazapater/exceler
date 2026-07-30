"""Create discovery_sources and audit_events.

Revision ID: 0001_phase1_sources
Revises:
Create Date: 2026-07-30

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_phase1_sources"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("endpoint", sa.String(length=1024), nullable=True),
        sa.Column("root_location", sa.String(length=2048), nullable=False),
        sa.Column("authentication_type", sa.String(length=64), nullable=False),
        sa.Column("credential_reference", sa.String(length=1024), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("read_only", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("recursive", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "include_patterns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "exclude_patterns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("max_depth", sa.Integer(), nullable=True),
        sa.Column("max_files_per_run", sa.Integer(), nullable=True),
        sa.Column("max_file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("scan_policy", sa.String(length=64), nullable=False),
        sa.Column(
            "connector_settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.create_index("ix_discovery_sources_name", "discovery_sources", ["name"])
    op.create_index(
        "ux_discovery_sources_active_name",
        "discovery_sources",
        ["name"],
        unique=True,
        postgresql_where=sa.text("archived_at IS NULL"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_entity", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ux_discovery_sources_active_name", table_name="discovery_sources")
    op.drop_index("ix_discovery_sources_name", table_name="discovery_sources")
    op.drop_table("discovery_sources")
