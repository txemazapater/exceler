"""Relationship / key discovery enums (Phase 2D)."""

from __future__ import annotations

from enum import StrEnum


class RelationshipCardinality(StrEnum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"
    UNKNOWN = "unknown"


class KeyKind(StrEnum):
    PRIMARY = "primary"
    COMPOSITE = "composite"
    NATURAL = "natural"
    SURROGATE = "surrogate"


class GraphNodeKind(StrEnum):
    WORKBOOK = "workbook"
    WORKSHEET = "worksheet"
    REGION = "region"
    COLUMN = "column"


class GraphEdgeKind(StrEnum):
    CONTAINS = "contains"
    CANDIDATE_KEY = "candidate_key"
    CANDIDATE_FOREIGN_KEY = "candidate_foreign_key"
    CANDIDATE_RELATIONSHIP = "candidate_relationship"


class Exactness(StrEnum):
    EXACT = "exact"
    TRUNCATED = "truncated"
    ESTIMATED = "estimated"
