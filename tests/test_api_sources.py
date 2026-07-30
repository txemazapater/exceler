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


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_source_crud_and_validate(
    client: TestClient, source_root: Path, db_session: Session
) -> None:
    payload = {
        "name": "comercial",
        "root_location": str(source_root).replace("\\", "/"),
        "read_only": True,
        "include_patterns": ["*.xlsx"],
        "exclude_patterns": ["~$*"],
    }
    created = client.post("/api/v1/sources", json=payload)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "comercial"
    assert "password" not in created.text.lower()
    source_id = body["id"]

    listed = client.get("/api/v1/sources")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    fetched = client.get(f"/api/v1/sources/{source_id}")
    assert fetched.status_code == 200

    validated = client.post(f"/api/v1/sources/{source_id}/validate")
    assert validated.status_code == 200
    assert validated.json()["valid"] is True

    disabled = client.patch(f"/api/v1/sources/{source_id}/status", json={"enabled": False})
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    archived = client.delete(f"/api/v1/sources/{source_id}")
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None

    audits = db_session.execute(text("select count(*) from audit_events")).scalar_one()
    assert int(audits) >= 3
