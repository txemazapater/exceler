from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

from exceler.domain.workbook.errors import (
    UnsupportedWorkbookFormatError,
    WorkbookAccessDeniedError,
    WorkbookNotFoundError,
)

SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm"}


class LocalWorkbookSource:
    """Local filesystem workbook source for Phase 2A."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    @property
    def name(self) -> str:
        return self._path.name

    @property
    def suggested_extension(self) -> str:
        return self._path.suffix.lower()

    def open_binary(self) -> BinaryIO:
        self._ensure_exists()
        try:
            return self._path.open("rb")
        except PermissionError as exc:
            raise WorkbookAccessDeniedError("Workbook file is not accessible.") from exc
        except OSError as exc:
            raise WorkbookAccessDeniedError("Workbook file is not accessible.") from exc

    def size_bytes(self) -> int:
        self._ensure_exists()
        return self._path.stat().st_size

    def content_hash(self) -> str:
        """Utility hash of the current file bytes.

        Not part of WorkbookSource protocol. Inspectors must hash the payload they read,
        not call this method (avoids a second snapshot that could diverge).
        """
        digest = hashlib.sha256()
        with self.open_binary() as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def modified_at_iso(self) -> str | None:
        self._ensure_exists()
        ts = self._path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=UTC).isoformat()

    def source_path(self) -> str | None:
        return str(self._path)

    def _ensure_exists(self) -> None:
        if self._path.is_dir():
            raise UnsupportedWorkbookFormatError("Path points to a directory, not a workbook.")
        if not self._path.exists():
            raise WorkbookNotFoundError("Workbook file was not found.")
        if self._path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise UnsupportedWorkbookFormatError(
                f"Unsupported workbook extension: {self._path.suffix or '(none)'}"
            )
