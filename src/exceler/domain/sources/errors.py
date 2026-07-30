from __future__ import annotations


class DomainError(Exception):
    """Base domain error."""


class SourceValidationError(DomainError):
    def __init__(self, message: str, *, code: str = "source_validation_error") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class SourceNotFoundError(DomainError):
    def __init__(self, source_id: str) -> None:
        super().__init__(f"Source not found: {source_id}")
        self.code = "source_not_found"
        self.source_id = source_id


class SourceConflictError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "source_conflict"
        self.message = message
