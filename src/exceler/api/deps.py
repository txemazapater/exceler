from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from exceler.application.sources.service import SourceService
from exceler.config.settings import Settings, get_settings
from exceler.infrastructure.db.models import SqlAlchemyAuditLogger, SqlAlchemySourceRepository
from exceler.infrastructure.db.session import create_db_engine, create_session_factory

_engine = None
_session_factory = None


def _ensure_engine(settings: Settings):  # type: ignore[no-untyped-def]
    global _engine, _session_factory
    if _engine is None:
        _engine = create_db_engine(settings)
        _session_factory = create_session_factory(_engine)
    return _session_factory


def get_db_session(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Generator[Session, None, None]:
    factory = _ensure_engine(settings)
    assert factory is not None
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_source_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SourceService:
    return SourceService(
        SqlAlchemySourceRepository(session),
        SqlAlchemyAuditLogger(session),
        allowed_source_roots=settings.allowed_roots_list(),
    )


def require_dev_token_if_configured(
    settings: Annotated[Settings, Depends(get_settings)],
    x_exceler_token: Annotated[str | None, Header(alias="X-Exceler-Token")] = None,
) -> None:
    """Optional development gate. Not a production auth system."""
    if settings.api_dev_token and x_exceler_token != settings.api_dev_token:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Exceler-Token")
