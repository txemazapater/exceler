from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from exceler.config.settings import get_settings, resolve_secret_reference
from exceler.main import create_app

pytestmark = pytest.mark.unit


def test_resolve_env_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXCELER_DB_PASSWORD", "from-env")
    assert resolve_secret_reference("env://EXCELER_DB_PASSWORD") == "from-env"


def test_resolve_file_secret(tmp_path: Path) -> None:
    secret_file = tmp_path / "db_password"
    secret_file.write_text("from-file\n", encoding="utf-8")
    assert resolve_secret_reference(f"file://{secret_file}") == "from-file"


def test_gitignore_excludes_secrets() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "secrets/*" in gitignore
    assert ".env" in gitignore
    assert "!secrets/*.example" in gitignore


def test_health_live_without_db_dependency() -> None:
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "live"
        compat = client.get("/health")
        assert compat.status_code == 200


def test_health_ready_reports_not_ready_without_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXCELER_ALLOWED_SOURCE_ROOTS", "/sources")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("EXCELER_DB_PASSWORD", raising=False)
    monkeypatch.delenv("EXCELER_DB_PASSWORD_REF", raising=False)
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "not_ready"
        assert body["checks"]["database"] == "unavailable"
    get_settings.cache_clear()
