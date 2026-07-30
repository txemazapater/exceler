from __future__ import annotations

from fastapi import FastAPI

from exceler.api.errors import install_exception_handlers
from exceler.api.health import router as health_router
from exceler.api.sources import router as sources_router
from exceler.config.settings import configure_logging, get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="EXCELER",
        version="0.1.0",
        description="Discovery source registry (Phase 1)",
    )
    install_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(sources_router)
    return app


app = create_app()
