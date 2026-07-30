from __future__ import annotations

from typing import BinaryIO, Protocol

from exceler.domain.workbook.models import WorkbookInspection, WorkbookInspectionOptions


class WorkbookSource(Protocol):
    """Binary workbook source. Identity of an inspection is derived from one payload read."""

    @property
    def name(self) -> str: ...

    @property
    def suggested_extension(self) -> str: ...

    def open_binary(self) -> BinaryIO: ...

    def size_bytes(self) -> int:
        """Announced size for pre-read limit checks (may differ from len(payload))."""
        ...

    def modified_at_iso(self) -> str | None: ...

    def source_path(self) -> str | None: ...


class WorkbookReader(Protocol):
    def inspect(
        self,
        source: WorkbookSource,
        options: WorkbookInspectionOptions | None = None,
    ) -> WorkbookInspection: ...
