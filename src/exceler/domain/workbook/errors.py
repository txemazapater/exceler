from __future__ import annotations

from exceler.domain.sources.errors import DomainError


class WorkbookInspectionError(DomainError):
    """Base error for workbook inspection."""

    code = "WORKBOOK_INSPECTION_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class WorkbookNotFoundError(WorkbookInspectionError):
    code = "WORKBOOK_NOT_FOUND"

    def __init__(self, message: str = "Workbook file was not found.") -> None:
        super().__init__(message, code=self.code)


class WorkbookAccessDeniedError(WorkbookInspectionError):
    code = "WORKBOOK_ACCESS_DENIED"

    def __init__(self, message: str = "Workbook file is not accessible.") -> None:
        super().__init__(message, code=self.code)


class UnsupportedWorkbookFormatError(WorkbookInspectionError):
    code = "UNSUPPORTED_WORKBOOK_FORMAT"

    def __init__(self, message: str = "Workbook format is not supported.") -> None:
        super().__init__(message, code=self.code)


class InvalidWorkbookError(WorkbookInspectionError):
    code = "INVALID_WORKBOOK"

    def __init__(self, message: str = "The file is not a valid XLSX/XLSM workbook.") -> None:
        super().__init__(message, code=self.code)


class EncryptedWorkbookError(WorkbookInspectionError):
    code = "ENCRYPTED_WORKBOOK"

    def __init__(self, message: str = "Encrypted workbooks are not supported.") -> None:
        super().__init__(message, code=self.code)


class WorkbookLimitExceededError(WorkbookInspectionError):
    code = "WORKBOOK_LIMIT_EXCEEDED"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.code)
