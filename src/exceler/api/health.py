from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import create_engine, text

from exceler.config.settings import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Compatibility alias for liveness. Prefer /health/live and /health/ready."""
    return {"status": "ok", "service": "exceler", "kind": "liveness"}


@router.get("/health/live")
def health_live() -> dict[str, str]:
    """Process liveness — does not depend on PostgreSQL or external mounts."""
    return {"status": "live", "service": "exceler"}


@router.get("/health/ready")
def health_ready(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    """Readiness — requires database connectivity and basic configuration."""
    checks: dict[str, str] = {}

    if settings.allowed_roots_list():
        checks["configuration"] = "ok"
    else:
        checks["configuration"] = "missing_allowed_source_roots"

    try:
        engine = create_engine(settings.resolved_database_url(), pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = "ok"
        engine.dispose()
    except Exception:  # noqa: BLE001 — readiness must report, not raise
        checks["database"] = "unavailable"

    ready = all(value == "ok" for value in checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "not_ready",
        "checks": checks,
    }
