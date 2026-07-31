"""Relationship domain errors (Phase 2D)."""

from __future__ import annotations


class RelationshipError(Exception):
    code: str = "RELATIONSHIP_ERROR"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class RelationshipInputMismatchError(RelationshipError):
    code = "RELATIONSHIP_INPUT_MISMATCH"


class UnsupportedRelationshipInputVersionError(RelationshipError):
    code = "UNSUPPORTED_RELATIONSHIP_INPUT"


class InvalidRelationshipContractError(RelationshipError):
    code = "INVALID_RELATIONSHIP_CONTRACT"
