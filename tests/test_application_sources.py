from __future__ import annotations

from pathlib import Path

import pytest
from tests.fakes import InMemorySourceRepository, RecordingAuditLogger

from exceler.application.sources.dto import SourceCreate, SourceUpdate
from exceler.application.sources.service import SourceService
from exceler.domain.sources.errors import SourceConflictError, SourceValidationError

pytestmark = pytest.mark.unit


@pytest.fixture()
def allowed_root(tmp_path: Path) -> Path:
    root = tmp_path / "sources"
    root.mkdir()
    return root


@pytest.fixture()
def service(allowed_root: Path) -> tuple[SourceService, RecordingAuditLogger]:
    audit = RecordingAuditLogger()
    svc = SourceService(
        InMemorySourceRepository(),
        audit,
        allowed_source_roots=[str(allowed_root)],
    )
    return svc, audit


def test_create_update_validate_with_in_memory_repo(
    service: tuple[SourceService, RecordingAuditLogger], allowed_root: Path
) -> None:
    svc, audit = service
    missing = allowed_root / "future"
    created = svc.create(
        SourceCreate(
            name="comercial",
            root_location=str(missing),
            read_only=True,
            credential_reference="env://EXCELER_EXAMPLE_SECRET",
        )
    )
    assert created.name == "comercial"
    assert created.credential_reference == "env://EXCELER_EXAMPLE_SECRET"

    report = svc.validate(created.id)
    assert report.configuration_valid is True
    assert report.accessible is False
    assert report.valid is False
    assert report.errors[0].code == "root_missing"

    present = allowed_root / "comercial"
    present.mkdir()
    updated = svc.update(created.id, SourceUpdate(root_location=str(present)))
    assert updated.root_location == str(present)
    ok = svc.validate(updated.id)
    assert ok.valid is True

    archived = svc.archive(updated.id)
    assert archived.is_archived is True
    with pytest.raises(SourceConflictError):
        svc.update(updated.id, SourceUpdate(name="nope"))

    actions = [event["action"] for event in audit.events]
    assert "source.created" in actions
    assert "source.validated" in actions
    assert "source.archived" in actions
    for event in audit.events:
        details = str(event.get("details", {}))
        assert "password=" not in details.lower()


def test_create_rejects_invalid_configuration(
    service: tuple[SourceService, RecordingAuditLogger], allowed_root: Path
) -> None:
    svc, _ = service
    with pytest.raises(SourceValidationError):
        svc.create(
            SourceCreate(
                name="bad",
                root_location=str(allowed_root / "x"),
                read_only=False,
            )
        )
