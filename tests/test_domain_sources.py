from __future__ import annotations

from pathlib import Path

import pytest

from exceler.domain.sources.enums import SourceType
from exceler.domain.sources.errors import SourceConflictError, SourceValidationError
from exceler.domain.sources.models import DiscoverySource
from exceler.domain.sources.validation import (
    probe_filesystem_accessibility,
    validate_credential_reference,
    validate_source_configuration,
)

pytestmark = pytest.mark.unit


def _source(**kwargs: object) -> DiscoverySource:
    base = {
        "name": "x",
        "source_type": SourceType.FILESYSTEM,
        "root_location": "/sources/samples",
    }
    base.update(kwargs)
    return DiscoverySource(**base)  # type: ignore[arg-type]


def test_read_only_required() -> None:
    with pytest.raises(SourceValidationError) as exc:
        validate_source_configuration(_source(read_only=False))
    assert exc.value.code == "read_only_required"


def test_rejects_bare_secret_credential_reference() -> None:
    with pytest.raises(SourceValidationError) as exc:
        validate_credential_reference("super-secret-password")
    assert exc.value.code == "invalid_credential_reference"


def test_rejects_malformed_env_credential_reference() -> None:
    with pytest.raises(SourceValidationError) as exc:
        validate_credential_reference("env://PASSWORD=supersecret")
    assert exc.value.code == "invalid_credential_reference"


def test_accepts_env_and_file_credential_references() -> None:
    validate_credential_reference("env://EXCELER_DB_PASSWORD")
    validate_credential_reference("file:///run/secrets/db_password")


def test_rejects_relative_root() -> None:
    with pytest.raises(SourceValidationError) as exc:
        validate_source_configuration(_source(root_location="sources/samples"))
    assert exc.value.code == "root_not_absolute"


def test_rejects_path_traversal(tmp_path: Path) -> None:
    allowed = tmp_path / "sources"
    allowed.mkdir()
    with pytest.raises(SourceValidationError) as exc:
        validate_source_configuration(
            _source(root_location=str(allowed / ".." / "other")),
            allowed_source_roots=[str(allowed)],
        )
    assert exc.value.code in {"root_path_traversal", "root_outside_allowed", "root_not_absolute"}


def test_config_allows_missing_path(tmp_path: Path) -> None:
    allowed = tmp_path / "sources"
    allowed.mkdir()
    missing = allowed / "not-mounted-yet"
    validate_source_configuration(
        _source(root_location=str(missing)),
        allowed_source_roots=[str(allowed)],
    )


def test_accessibility_missing_path(tmp_path: Path) -> None:
    allowed = tmp_path / "sources"
    allowed.mkdir()
    missing = allowed / "gone"
    report = probe_filesystem_accessibility(str(missing), [str(allowed)])
    assert report.configuration_valid is True
    assert report.accessible is False
    assert report.valid is False
    assert any(err.code == "root_missing" for err in report.errors)


def test_accessibility_ok(tmp_path: Path) -> None:
    allowed = tmp_path / "sources"
    root = allowed / "comercial"
    root.mkdir(parents=True)
    (root / "dummy.txt").write_text("ok", encoding="utf-8")
    report = probe_filesystem_accessibility(str(root), [str(allowed)])
    assert report.valid is True
    assert report.checks["readable"] is True


def test_outside_allowed_roots(tmp_path: Path) -> None:
    allowed = tmp_path / "sources"
    allowed.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(SourceValidationError) as exc:
        validate_source_configuration(
            _source(root_location=str(other)),
            allowed_source_roots=[str(allowed)],
        )
    assert exc.value.code == "root_outside_allowed"


def test_include_patterns_empty_rejected() -> None:
    with pytest.raises(SourceValidationError) as exc:
        validate_source_configuration(_source(include_patterns=[""]))
    assert exc.value.code == "invalid_pattern"


def test_reconfigure_protects_fields_and_archived() -> None:
    source = _source()
    created = source.created_at
    source_id = source.id
    source.reconfigure({"name": " renamed ", "max_depth": 3})
    assert source.name == "renamed"
    assert source.max_depth == 3
    assert source.id == source_id
    assert source.created_at == created
    with pytest.raises(SourceValidationError):
        source.reconfigure({"id": source_id})
    source.archive()
    with pytest.raises(SourceConflictError):
        source.reconfigure({"name": "nope"})
