from __future__ import annotations

import json
import logging
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def resolve_secret_reference(ref: str | None, *, fallback: str | None = None) -> str | None:
    """Resolve env://VAR or file:///path secret references. Never log the value."""
    if ref is None or ref == "":
        return fallback
    if ref.startswith("env://"):
        import os

        key = ref.removeprefix("env://")
        return os.environ.get(key, fallback)
    if ref.startswith("file://"):
        path = Path(ref.removeprefix("file://"))
        if not path.exists():
            return fallback
        return path.read_text(encoding="utf-8").strip()
    # Plain value allowed for local development only; prefer references.
    return ref


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    exceler_env: str = Field(default="development", alias="EXCELER_ENV")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    database_url_ref: str | None = Field(default=None, alias="DATABASE_URL_REF")
    db_password_ref: str | None = Field(default=None, alias="EXCELER_DB_PASSWORD_REF")
    db_password: str | None = Field(default=None, alias="EXCELER_DB_PASSWORD")
    db_host: str = Field(default="exceler-db", alias="EXCELER_DB_HOST")
    db_port: int = Field(default=5432, alias="EXCELER_DB_PORT")
    db_name: str = Field(default="exceler", alias="EXCELER_DB_NAME")
    db_user: str = Field(default="exceler", alias="EXCELER_DB_USER")
    allowed_source_roots: str = Field(default="/sources", alias="EXCELER_ALLOWED_SOURCE_ROOTS")
    log_level: str = Field(default="INFO", alias="EXCELER_LOG_LEVEL")
    auto_migrate: bool = Field(default=False, alias="EXCELER_AUTO_MIGRATE")
    api_dev_token: str | None = Field(default=None, alias="EXCELER_API_DEV_TOKEN")

    @field_validator("auto_migrate", mode="before")
    @classmethod
    def parse_bool(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value

    def allowed_roots_list(self) -> list[str]:
        return [part.strip() for part in self.allowed_source_roots.split(",") if part.strip()]

    def resolved_database_url(self) -> str:
        if self.database_url_ref:
            resolved = resolve_secret_reference(self.database_url_ref)
            if resolved:
                return resolved
        if self.database_url:
            return self.database_url
        password = resolve_secret_reference(
            self.db_password_ref,
            fallback=self.db_password,
        )
        if not password:
            raise RuntimeError(
                "Database password not configured. Set DATABASE_URL, "
                "EXCELER_DB_PASSWORD_REF, or EXCELER_DB_PASSWORD."
            )
        return (
            f"postgresql+psycopg://{self.db_user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


class JsonLogFormatter(logging.Formatter):
    SENSITIVE_KEYS = ("password", "secret", "token", "authorization", "database_url")

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in {
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "name",
                "taskName",
            }:
                continue
            payload[key] = self._redact(key, value)
        return json.dumps(payload, default=str)

    def _redact(self, key: str, value: Any) -> Any:
        lowered = key.lower()
        if any(part in lowered for part in self.SENSITIVE_KEYS):
            return "***"
        if isinstance(value, str) and any(
            part in value.lower() for part in ("password=", "secret=", "token=")
        ):
            return "***"
        return value


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())
