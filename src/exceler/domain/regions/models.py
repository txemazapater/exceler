"""Region detection domain (Phase 2B) — logical regions from WorkbookInspection only."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RegionType(StrEnum):
    UNKNOWN = "unknown"
    TABLE = "table"
    MATRIX = "matrix"
    FORM = "form"
    HEADER = "header"
    FOOTER = "footer"
    NOTE = "note"
    TITLE = "title"
    CHART_AREA = "chart_area"
    PIVOT_LIKE = "pivot_like"
    IMAGE_PLACEHOLDER = "image_placeholder"


@dataclass(frozen=True)
class BoundingBox:
    first_row: int
    last_row: int
    first_col: int
    last_col: int

    def to_dict(self) -> dict[str, int]:
        return {
            "first_row": self.first_row,
            "last_row": self.last_row,
            "first_col": self.first_col,
            "last_col": self.last_col,
        }


@dataclass(frozen=True)
class RegionEvidenceItem:
    code: str
    weight: float
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "weight": self.weight, "message": self.message}


@dataclass(frozen=True)
class RegionStyleProfile:
    distinct_fill_colors: int = 0
    distinct_font_names: int = 0
    bold_cell_ratio: float = 0.0
    bordered_cell_ratio: float = 0.0
    dominant_fill_color: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "distinct_fill_colors": self.distinct_fill_colors,
            "distinct_font_names": self.distinct_font_names,
            "bold_cell_ratio": self.bold_cell_ratio,
            "bordered_cell_ratio": self.bordered_cell_ratio,
            "dominant_fill_color": self.dominant_fill_color,
        }


@dataclass(frozen=True)
class RegionStatistics:
    """Occupancy counts are layered — do not treat them as interchangeable.

    - observed_count: cells present in WorkbookInspection.cells inside the bbox
    - content_occupied_count: cells with value/formula (content occupancy)
    - visual_occupied_count: content + styled empties + merge coverage (visual occupancy)
    - occupied_count: alias of content_occupied_count (legacy name)
    - density / empty_ratio: based on content occupancy vs bbox area
    - visual_density: visual occupancy vs bbox area
    """

    cell_count: int
    observed_count: int
    content_occupied_count: int
    visual_occupied_count: int
    occupied_count: int
    empty_ratio: float
    formula_ratio: float
    density: float
    visual_density: float
    row_count: int
    column_count: int
    distinct_value_kinds: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_count": self.cell_count,
            "observed_count": self.observed_count,
            "content_occupied_count": self.content_occupied_count,
            "visual_occupied_count": self.visual_occupied_count,
            "occupied_count": self.occupied_count,
            "empty_ratio": self.empty_ratio,
            "formula_ratio": self.formula_ratio,
            "density": self.density,
            "visual_density": self.visual_density,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "distinct_value_kinds": self.distinct_value_kinds,
        }


@dataclass(frozen=True)
class LogicalRegion:
    id: str
    sheet_name: str
    bounding_box: BoundingBox
    region_type: RegionType
    confidence: float
    parent_id: str | None
    children_ids: tuple[str, ...]
    header_row_indices: tuple[int, ...]
    footer_row_indices: tuple[int, ...]
    cell_coordinates: tuple[str, ...]
    style_profile: RegionStyleProfile
    statistics: RegionStatistics
    evidence: tuple[RegionEvidenceItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sheet_name": self.sheet_name,
            "bounding_box": self.bounding_box.to_dict(),
            "region_type": self.region_type.value,
            "confidence": self.confidence,
            "parent_id": self.parent_id,
            "children_ids": list(self.children_ids),
            "header_row_indices": list(self.header_row_indices),
            "footer_row_indices": list(self.footer_row_indices),
            "cell_coordinates": list(self.cell_coordinates),
            "style_profile": self.style_profile.to_dict(),
            "statistics": self.statistics.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class SheetRegions:
    sheet_name: str
    sheet_index: int
    regions: tuple[LogicalRegion, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sheet_name": self.sheet_name,
            "sheet_index": self.sheet_index,
            "regions": [region.to_dict() for region in self.regions],
        }


@dataclass(frozen=True)
class RegionDetectionResult:
    workbook_hash: str
    inspector_version: str
    detector_version: str
    regions_schema_version: int
    sheets: tuple[SheetRegions, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)
    limitations: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "regions_schema_version": self.regions_schema_version,
            "workbook_hash": self.workbook_hash,
            "inspector_version": self.inspector_version,
            "detector_version": self.detector_version,
            "sheets": [sheet.to_dict() for sheet in self.sheets],
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }
