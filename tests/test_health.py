from __future__ import annotations

from fastapi.testclient import TestClient

from exceler.config.settings import get_settings
from exceler.main import create_app


def test_health_ready_reports_not_ready_without_database(monkeypatch: object) -> None:
    monkeypatch.setenv("EXCELER_ALLOWED_SOURCE_ROOTS", "/sources")  # type: ignore[attr-defined]
    monkeypatch.delenv("DATABASE_URL", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("EXCELER_DB_PASSWORD", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("EXCELER_DB_PASSWORD_REF", raising=False)  # type: ignore[attr-defined]
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "not_ready"
        assert body["checks"]["database"] == "unavailable"
    get_settings.cache_clear()
