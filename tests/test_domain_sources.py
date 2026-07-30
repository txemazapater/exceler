from __future__ import annotations

from pathlib import Path

import pytest

from exceler.domain.sources.enums import AuthenticationType, SourceType
from exceler.domain.sources.errors import SourceValidationError
from exceler.domain.sources.models import DiscoverySource
from exceler.domain.sources.validation import (
    validate_filesystem_accessibility,
    validate_source_invariants,
)


def test_read_only_required() -> None:
    source = DiscoverySource(
        name="x",
        source_type=SourceType.FILESYSTEM,
        root_location="/sources/samples",
        read_only=False,
    )
    with pytest.raises(SourceValidationError) as exc:
        validate_source_invariants(source)
    assert exc.value.code == "read_only_required"


def test_rejects_secret_material_in_credential_reference() -> None:
    source = DiscoverySource(
        name="x",
        source_type=SourceType.FILESYSTEM,
        root_location="/sources/samples",
        authentication_type=AuthenticationType.CREDENTIAL_REFERENCE,
        credential_reference="env://PASSWORD=supersecret",
    )
    with pytest.raises(SourceValidationError) as exc:
        validate_source_invariants(source)
    assert exc.value.code == "secret_in_credential_reference"


def test_rejects_relative_root() -> None:
    source = DiscoverySource(
        name="x",
        source_type=SourceType.FILESYSTEM,
        root_location="sources/samples",
    )
    with pytest.raises(SourceValidationError) as exc:
        validate_source_invariants(source)
    assert exc.value.code == "root_not_absolute"


def test_filesystem_accessibility(tmp_path: Path) -> None:
    allowed = tmp_path / "sources"
    root = allowed / "comercial"
    root.mkdir(parents=True)
    (root / "dummy.txt").write_text("ok", encoding="utf-8")
    checks = validate_filesystem_accessibility(str(root), [str(allowed)])
    assert checks["readable"] is True


def test_outside_allowed_roots(tmp_path: Path) -> None:
    allowed = tmp_path / "sources"
    allowed.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(SourceValidationError) as exc:
        validate_filesystem_accessibility(str(other), [str(allowed)])
    assert exc.value.code == "root_outside_allowed"


def test_include_patterns_empty_rejected() -> None:
    source = DiscoverySource(
        name="x",
        source_type=SourceType.FILESYSTEM,
        root_location="/sources/samples",
        include_patterns=[""],
    )
    with pytest.raises(SourceValidationError) as exc:
        validate_source_invariants(source)
    assert exc.value.code == "invalid_pattern"
