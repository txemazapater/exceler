from __future__ import annotations

from pathlib import Path

from exceler.config.settings import resolve_secret_reference


def test_resolve_env_secret(monkeypatch: object) -> None:
    monkeypatch.setenv("EXCELER_DB_PASSWORD", "from-env")  # type: ignore[attr-defined]
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
