from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from exceler.api.deps import get_db_session, get_source_service
from exceler.application.sources.service import SourceService
from exceler.config.settings import get_settings
from exceler.infrastructure.db.models import Base, SqlAlchemyAuditLogger, SqlAlchemySourceRepository
from exceler.main import create_app

pytestmark = pytest.mark.integration


def _database_url() -> str | None:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")


@pytest.fixture(scope="session")
def database_url() -> str:
    url = _database_url()
    if not url:
        pytest.skip("TEST_DATABASE_URL / DATABASE_URL not set")
    return url


@pytest.fixture()
def db_session(database_url: str) -> Generator[Session, None, None]:
    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def source_root(tmp_path: Path) -> Path:
    root = tmp_path / "sources" / "comercial"
    root.mkdir(parents=True)
    (root / "note.txt").write_text("synthetic", encoding="utf-8")
    return root


@pytest.fixture()
def client(
    db_session: Session, source_root: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    allowed = str(source_root.parent)
    monkeypatch.setenv("EXCELER_ALLOWED_SOURCE_ROOTS", allowed)
    monkeypatch.setenv("DATABASE_URL", _database_url() or "")
    get_settings.cache_clear()

    app = create_app()

    def override_session() -> Generator[Session, None, None]:
        yield db_session

    def override_service() -> SourceService:
        return SourceService(
            SqlAlchemySourceRepository(db_session),
            SqlAlchemyAuditLogger(db_session),
            allowed_source_roots=[allowed],
        )

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_source_service] = override_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_health_ready(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "ok"


def test_source_crud_and_validate(
    client: TestClient, source_root: Path, db_session: Session
) -> None:
    payload = {
        "name": "comercial",
        "root_location": str(source_root).replace("\\", "/"),
        "read_only": True,
        "include_patterns": ["*.xlsx"],
        "exclude_patterns": ["~$*"],
        "credential_reference": "env://EXCELER_EXAMPLE_SECRET",
    }
    created = client.post("/api/v1/sources", json=payload)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["credential_reference"] == "env://EXCELER_EXAMPLE_SECRET"
    source_id = body["id"]

    missing = source_root.parent / "not-yet-mounted"
    updated = client.put(
        f"/api/v1/sources/{source_id}",
        json={"root_location": str(missing).replace("\\", "/")},
    )
    assert updated.status_code == 200, updated.text

    validated_missing = client.post(f"/api/v1/sources/{source_id}/validate")
    assert validated_missing.status_code == 200
    missing_body = validated_missing.json()
    assert missing_body["configuration_valid"] is True
    assert missing_body["accessible"] is False
    assert missing_body["valid"] is False
    assert missing_body["errors"][0]["code"] == "root_missing"

    restored = client.put(
        f"/api/v1/sources/{source_id}",
        json={"root_location": str(source_root).replace("\\", "/")},
    )
    assert restored.status_code == 200
    validated = client.post(f"/api/v1/sources/{source_id}/validate")
    assert validated.status_code == 200
    assert validated.json()["valid"] is True

    archived = client.delete(f"/api/v1/sources/{source_id}")
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    blocked = client.put(f"/api/v1/sources/{source_id}", json={"name": "nope"})
    assert blocked.status_code == 409

    audits = db_session.execute(text("select count(*) from audit_events")).scalar_one()
    assert int(audits) >= 3


def test_create_missing_path_ok(client: TestClient, source_root: Path) -> None:
    missing = source_root.parent / "future-share"
    created = client.post(
        "/api/v1/sources",
        json={
            "name": "future",
            "root_location": str(missing).replace("\\", "/"),
            "read_only": True,
        },
    )
    assert created.status_code == 201, created.text
