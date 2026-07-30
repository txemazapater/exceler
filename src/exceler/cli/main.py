from __future__ import annotations

import typer
from alembic import command
from alembic.config import Config

from exceler.application.sources.service import SourceService
from exceler.config.settings import configure_logging, get_settings
from exceler.infrastructure.db.models import SqlAlchemyAuditLogger, SqlAlchemySourceRepository
from exceler.infrastructure.db.session import create_db_engine, create_session_factory

app = typer.Typer(help="EXCELER administrative CLI", no_args_is_help=True)
db_app = typer.Typer(help="Database commands")
source_app = typer.Typer(help="Discovery source commands")
dev_app = typer.Typer(help="Development utilities (requires checkout with tests/)")
fixtures_app = typer.Typer(help="Synthetic Excel fixtures")
app.add_typer(db_app, name="db")
app.add_typer(source_app, name="source")
app.add_typer(dev_app, name="dev")
dev_app.add_typer(fixtures_app, name="fixtures")


@fixtures_app.command("generate")
def fixtures_generate() -> None:
    """Generate deterministic synthetic workbooks, manifests and expected skeletons."""
    _ensure_tests_importable()
    from tests.generators.generate_fixtures import main as generate_main

    generate_main()


@fixtures_app.command("verify")
def fixtures_verify() -> None:
    """Verify fixture catalog integrity and regeneration stability."""
    _ensure_tests_importable()
    from tests.generators.verify_fixtures import main as verify_main

    verify_main()


def _ensure_tests_importable() -> None:
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    if not (repo / "tests" / "generators").is_dir():
        raise RuntimeError(
            "tests/generators not found. Run fixture commands from a full repository checkout."
        )
    repo_str = str(repo)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)


def _alembic_config() -> Config:
    settings = get_settings()
    configure_logging(settings.log_level)
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.resolved_database_url())
    return cfg


def _source_service() -> tuple[SourceService, object]:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(settings)
    factory = create_session_factory(engine)
    session = factory()
    service = SourceService(
        SqlAlchemySourceRepository(session),
        SqlAlchemyAuditLogger(session),
        allowed_source_roots=settings.allowed_roots_list(),
    )
    return service, session


@db_app.command("upgrade")
def db_upgrade(revision: str = "head") -> None:
    """Apply Alembic migrations. Does not run automatically in production."""
    command.upgrade(_alembic_config(), revision)
    typer.echo(f"Upgraded database to {revision}")


@db_app.command("current")
def db_current() -> None:
    command.current(_alembic_config())


@source_app.command("list")
def source_list(include_archived: bool = False) -> None:
    service, session = _source_service()
    try:
        result = service.list(include_archived=include_archived, offset=0, limit=200)
        for item in result.items:
            status = "archived" if item.is_archived else ("enabled" if item.enabled else "disabled")
            typer.echo(f"{item.id}  {item.name}  {status}  {item.root_location}")
        typer.echo(f"total={result.total}")
    finally:
        session.close()  # type: ignore[attr-defined]


@source_app.command("validate")
def source_validate(source_id: str) -> None:
    from uuid import UUID

    service, session = _source_service()
    try:
        result = service.validate(UUID(source_id))
        typer.echo(
            f"valid={result.valid} configuration_valid={result.configuration_valid} "
            f"accessible={result.accessible} message={result.message}"
        )
        for key, value in result.checks.items():
            typer.echo(f"  check.{key}={value}")
        for err in result.errors:
            typer.echo(f"  error.{err.code}={err.message}")
    finally:
        session.close()  # type: ignore[attr-defined]


if __name__ == "__main__":
    app()
