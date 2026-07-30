"""Deterministic heuristic region detector — consumes WorkbookInspection only (no openpyxl)."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

from exceler.domain.regions.models import (
    BoundingBox,
    LogicalRegion,
    RegionDetectionResult,
    RegionEvidenceItem,
    RegionStatistics,
    RegionStyleProfile,
    RegionType,
    SheetRegions,
)
from exceler.domain.regions.options import (
    DETECTOR_VERSION,
    REGIONS_SCHEMA_VERSION,
    RegionDetectionOptions,
)
from exceler.domain.workbook.enums import CellValueKind
from exceler.domain.workbook.models import (
    MergedRangeInspection,
    WorkbookInspection,
    WorksheetInspection,
)

_A1_RE = re.compile(r"^([A-Z]+)(\d+)$", re.IGNORECASE)
_REF_RE = re.compile(
    r"^\$?([A-Z]+)\$?(\d+):\$?([A-Z]+)\$?(\d+)$",
    re.IGNORECASE,
)


def _col_letters_to_index(letters: str) -> int:
    value = 0
    for ch in letters.upper():
        value = value * 26 + (ord(ch) - ord("A") + 1)
    return value


def _index_to_col_letters(index: int) -> str:
    n = index
    letters: list[str] = []
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters.append(chr(ord("A") + rem))
    return "".join(reversed(letters))


def _coord(row: int, col: int) -> str:
    return f"{_index_to_col_letters(col)}{row}"


def _parse_a1(ref: str) -> tuple[int, int] | None:
    match = _A1_RE.match(ref.strip())
    if not match:
        return None
    return int(match.group(2)), _col_letters_to_index(match.group(1))


def _parse_range(ref: str) -> tuple[int, int, int, int] | None:
    match = _REF_RE.match(ref.replace(" ", ""))
    if not match:
        return None
    r1 = int(match.group(2))
    c1 = _col_letters_to_index(match.group(1))
    r2 = int(match.group(4))
    c2 = _col_letters_to_index(match.group(3))
    return min(r1, r2), max(r1, r2), min(c1, c2), max(c1, c2)


@dataclass
class _CellFact:
    coordinate: str
    row: int
    column: int
    kind: CellValueKind
    formula: str | None
    has_comment: bool
    font_bold: bool
    font_name: str | None
    font_size: float | None
    fill_color: str | None
    bordered: bool
    merge_id: str | None = None


class _UnionFind:
    def __init__(self, items: Iterable[tuple[int, int]]) -> None:
        self.parent = {item: item for item in items}
        self.rank = {item: 0 for item in items}

    def find(self, item: tuple[int, int]) -> tuple[int, int]:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, a: tuple[int, int], b: tuple[int, int]) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            self.parent[ra] = rb
        elif self.rank[ra] > self.rank[rb]:
            self.parent[rb] = ra
        else:
            self.parent[rb] = ra
            self.rank[ra] += 1


def _component_profile(cells: list[_CellFact]) -> tuple[str | None, float, float]:
    fills = [c.fill_color for c in cells if c.fill_color]
    dominant = Counter(fills).most_common(1)[0][0] if fills else None
    bold_ratio = sum(1 for c in cells if c.font_bold) / max(len(cells), 1)
    border_ratio = sum(1 for c in cells if c.bordered) / max(len(cells), 1)
    return dominant, bold_ratio, border_ratio


def _merge_score(
    left: list[_CellFact],
    right: list[_CellFact],
    *,
    gap: int,
    axis: str,
    options: RegionDetectionOptions,
) -> float:
    """Score whether two components separated by an empty gap should merge."""
    max_gap = options.max_weak_gap_rows if axis == "row" else options.max_weak_gap_cols
    if gap > max_gap:
        return 0.0
    if gap <= 0:
        return 1.0

    l_fill, l_bold, l_border = _component_profile(left)
    r_fill, r_bold, r_border = _component_profile(right)
    score = 0.35  # weak single-gap baseline (false interior gaps)

    if l_fill and r_fill and l_fill == r_fill:
        score += 0.35
    elif l_fill and r_fill and l_fill != r_fill:
        return 0.0  # hard style separator
    elif not l_fill and not r_fill:
        score += 0.1

    if abs(l_bold - r_bold) < 0.35:
        score += 0.1
    if abs(l_border - r_border) < 0.35:
        score += 0.15
    if l_border > 0.4 and r_border > 0.4:
        score += 0.2

    l_box = _bbox_of(left)
    r_box = _bbox_of(right)
    l_h = l_box.last_row - l_box.first_row + 1
    r_h = r_box.last_row - r_box.first_row + 1
    # Do not glue a title/note band onto a denser block across a gap.
    if (l_h <= 1 and len(left) <= 4 and r_h >= 2) or (r_h <= 1 and len(right) <= 4 and l_h >= 2):
        score -= 0.5

    l_rows = {c.row for c in left}
    r_rows = {c.row for c in right}
    l_cols = {c.column for c in left}
    r_cols = {c.column for c in right}
    if axis == "row":
        overlap = len(l_cols & r_cols) / max(len(l_cols | r_cols), 1)
        score += 0.2 * overlap
    else:
        overlap = len(l_rows & r_rows) / max(len(l_rows | r_rows), 1)
        score += 0.2 * overlap

    return max(0.0, min(1.0, score))


def _bbox_of(cells: list[_CellFact]) -> BoundingBox:
    return BoundingBox(
        first_row=min(c.row for c in cells),
        last_row=max(c.row for c in cells),
        first_col=min(c.column for c in cells),
        last_col=max(c.column for c in cells),
    )


def _build_facts(ws: WorksheetInspection) -> dict[tuple[int, int], _CellFact]:
    facts: dict[tuple[int, int], _CellFact] = {}
    for cell in ws.cells:
        style = cell.style
        facts[(cell.row, cell.column)] = _CellFact(
            coordinate=cell.coordinate,
            row=cell.row,
            column=cell.column,
            kind=cell.value.kind,
            formula=cell.formula,
            has_comment=cell.comment is not None,
            font_bold=bool(style and style.font_bold),
            font_name=style.font_name if style else None,
            font_size=style.font_size if style else None,
            fill_color=style.fill_color if style else None,
            bordered=bool(
                style
                and (
                    style.border_top
                    or style.border_right
                    or style.border_bottom
                    or style.border_left
                )
            ),
        )

    for merged in ws.merged_ranges:
        parsed = _parse_range(merged.reference)
        if parsed is None:
            continue
        r1, r2, c1, c2 = parsed
        anchor = _parse_a1(merged.anchor)
        anchor_fact = facts.get(anchor) if anchor else None
        for row in range(r1, r2 + 1):
            for col in range(c1, c2 + 1):
                key = (row, col)
                if key in facts:
                    facts[key].merge_id = merged.reference
                    continue
                if anchor_fact is not None:
                    facts[key] = _CellFact(
                        coordinate=_coord(row, col),
                        row=row,
                        column=col,
                        kind=anchor_fact.kind,
                        formula=None,
                        has_comment=False,
                        font_bold=anchor_fact.font_bold,
                        font_name=anchor_fact.font_name,
                        font_size=anchor_fact.font_size,
                        fill_color=anchor_fact.fill_color,
                        bordered=anchor_fact.bordered,
                        merge_id=merged.reference,
                    )
                else:
                    facts[key] = _CellFact(
                        coordinate=_coord(row, col),
                        row=row,
                        column=col,
                        kind=CellValueKind.NULL,
                        formula=None,
                        has_comment=False,
                        font_bold=False,
                        font_name=None,
                        font_size=None,
                        fill_color=None,
                        bordered=False,
                        merge_id=merged.reference,
                    )
    return facts


def _connected_components(
    facts: dict[tuple[int, int], _CellFact],
    options: RegionDetectionOptions,
) -> list[list[_CellFact]]:
    if not facts:
        return []
    keys = list(facts.keys())
    uf = _UnionFind(keys)
    key_set = set(keys)
    for row, col in keys:
        for dr, dc in ((0, 1), (1, 0)):
            neighbor = (row + dr, col + dc)
            if neighbor in key_set:
                uf.union((row, col), neighbor)

    groups: dict[tuple[int, int], list[_CellFact]] = defaultdict(list)
    for key in keys:
        groups[uf.find(key)].append(facts[key])
    components = list(groups.values())

    changed = True
    while changed:
        changed = False
        components.sort(key=lambda cells: (min(c.row for c in cells), min(c.column for c in cells)))
        merged_flags = [False] * len(components)
        next_components: list[list[_CellFact]] = []
        for i, left in enumerate(components):
            if merged_flags[i]:
                continue
            combined = list(left)
            lbox = _bbox_of(left)
            for j in range(i + 1, len(components)):
                if merged_flags[j]:
                    continue
                right = components[j]
                rbox = _bbox_of(right)
                if lbox.last_col >= rbox.first_col and rbox.last_col >= lbox.first_col:
                    if rbox.first_row > lbox.last_row:
                        gap = rbox.first_row - lbox.last_row - 1
                        score = _merge_score(left, right, gap=gap, axis="row", options=options)
                        if score >= options.merge_score_threshold:
                            combined.extend(right)
                            merged_flags[j] = True
                            changed = True
                            lbox = _bbox_of(combined)
                            continue
                    if lbox.first_row > rbox.last_row:
                        gap = lbox.first_row - rbox.last_row - 1
                        score = _merge_score(right, left, gap=gap, axis="row", options=options)
                        if score >= options.merge_score_threshold:
                            combined.extend(right)
                            merged_flags[j] = True
                            changed = True
                            lbox = _bbox_of(combined)
                            continue
                if lbox.last_row >= rbox.first_row and rbox.last_row >= lbox.first_row:
                    if rbox.first_col > lbox.last_col:
                        gap = rbox.first_col - lbox.last_col - 1
                        score = _merge_score(left, right, gap=gap, axis="col", options=options)
                        if score >= options.merge_score_threshold:
                            combined.extend(right)
                            merged_flags[j] = True
                            changed = True
                            lbox = _bbox_of(combined)
                    elif lbox.first_col > rbox.last_col:
                        gap = lbox.first_col - rbox.last_col - 1
                        score = _merge_score(right, left, gap=gap, axis="col", options=options)
                        if score >= options.merge_score_threshold:
                            combined.extend(right)
                            merged_flags[j] = True
                            changed = True
                            lbox = _bbox_of(combined)
            next_components.append(combined)
        components = next_components
    return components


def _column_kind_consistency(cells: list[_CellFact], bbox: BoundingBox) -> float:
    if bbox.last_col < bbox.first_col:
        return 0.0
    scores: list[float] = []
    by_col: dict[int, list[CellValueKind]] = defaultdict(list)
    for cell in cells:
        if cell.kind is not CellValueKind.NULL:
            by_col[cell.column].append(cell.kind)
    for col in range(bbox.first_col, bbox.last_col + 1):
        kinds = by_col.get(col, [])
        if len(kinds) <= 1:
            scores.append(1.0)
            continue
        dominant = Counter(kinds).most_common(1)[0][1]
        scores.append(dominant / len(kinds))
    return sum(scores) / max(len(scores), 1)


def _header_like(top_row: list[_CellFact]) -> bool:
    if not top_row:
        return False
    strings = sum(1 for c in top_row if c.kind is CellValueKind.STRING)
    bold = sum(1 for c in top_row if c.font_bold)
    filled = sum(1 for c in top_row if c.fill_color)
    n = len(top_row)
    return (strings / n >= 0.5) or (bold / n >= 0.4) or (filled / n >= 0.4)


def _classify(
    cells: list[_CellFact],
    bbox: BoundingBox,
    *,
    merges: tuple[MergedRangeInspection, ...],
    below_dense: bool,
) -> tuple[RegionType, list[RegionEvidenceItem], float]:
    evidence: list[RegionEvidenceItem] = []
    width = bbox.last_col - bbox.first_col + 1
    height = bbox.last_row - bbox.first_row + 1
    area = max(width * height, 1)
    occupied = len(cells)
    density = occupied / area
    comment_ratio = sum(1 for c in cells if c.has_comment) / max(occupied, 1)
    consistency = _column_kind_consistency(cells, bbox)
    top = [c for c in cells if c.row == bbox.first_row]
    headerish = _header_like(top)

    merge_wide = False
    for merged in merges:
        parsed = _parse_range(merged.reference)
        if parsed is None:
            continue
        r1, r2, c1, c2 = parsed
        if r1 == bbox.first_row == r2 and c1 <= bbox.first_col and c2 >= bbox.last_col:
            if (c2 - c1 + 1) >= max(2, width):
                merge_wide = True
                break
        if r1 == r2 == bbox.first_row and bbox.first_row == bbox.last_row and (c2 - c1 + 1) >= 2:
            if bbox.first_col >= c1 and bbox.last_col <= c2:
                merge_wide = True
                break

    title_score = 0.0
    if height <= 2 and occupied <= max(4, width) and (below_dense or merge_wide or width >= 2):
        title_score += 0.35
        evidence.append(
            RegionEvidenceItem("few_cells_title_band", 0.35, "Shallow band with few occupied cells")
        )
    if any(c.font_bold for c in cells):
        title_score += 0.2
        evidence.append(RegionEvidenceItem("bold_cells", 0.2, "Bold text present"))
    if merge_wide:
        title_score += 0.35
        evidence.append(RegionEvidenceItem("wide_merge", 0.35, "Wide merged range"))
    if below_dense and height <= 2:
        title_score += 0.25
        evidence.append(
            RegionEvidenceItem("above_dense_block", 0.25, "Sits immediately above denser block")
        )

    table_score = 0.0
    if height >= 2 and width >= 2:
        table_score += 0.25
        evidence.append(RegionEvidenceItem("min_table_shape", 0.25, "At least 2x2 shape"))
        if consistency >= 0.7:
            table_score += 0.3
            evidence.append(
                RegionEvidenceItem(
                    "column_kind_consistency",
                    0.3,
                    f"Column value-kind consistency={consistency:.2f}",
                )
            )
        if headerish:
            table_score += 0.3
            evidence.append(
                RegionEvidenceItem("header_like_top_row", 0.3, "Top row looks like header")
            )
        if density >= 0.45:
            table_score += 0.2
            evidence.append(RegionEvidenceItem("density", 0.2, f"Density={density:.2f}"))

    note_score = 0.0
    string_ratio = sum(1 for c in cells if c.kind is CellValueKind.STRING) / max(occupied, 1)
    if height <= 1 and string_ratio >= 0.5 and (below_dense or merge_wide):
        title_score += 0.3
        evidence.append(
            RegionEvidenceItem("single_row_string_band", 0.3, "Single-row string band")
        )
    if width <= 2 and string_ratio >= 0.8 and not below_dense and not merge_wide:
        note_score += 0.45
        evidence.append(
            RegionEvidenceItem("narrow_text_block", 0.45, "Narrow text block away from title context")
        )
    if density < 0.35 and width <= 3:
        note_score += 0.35
        evidence.append(RegionEvidenceItem("sparse_block", 0.35, "Sparse / narrow block"))
    if comment_ratio > 0:
        note_score += 0.25
        evidence.append(RegionEvidenceItem("comments", 0.25, "Comments present"))
    if occupied <= 4 and height >= 1 and width <= 2 and not below_dense:
        note_score += 0.2
        evidence.append(RegionEvidenceItem("short_text_block", 0.2, "Short text-like block"))
    if string_ratio >= 0.8 and width <= 2 and height >= 2 and not below_dense:
        note_score += 0.15
        evidence.append(RegionEvidenceItem("string_column", 0.15, "Mostly strings in narrow span"))

    scores = {
        RegionType.TITLE: title_score,
        RegionType.TABLE: table_score,
        RegionType.NOTE: note_score,
        RegionType.UNKNOWN: 0.15,
    }
    best_type = max(scores, key=lambda t: scores[t])
    best = scores[best_type]
    if best_type is RegionType.NOTE and table_score >= 0.55 and height >= 2 and width >= 2:
        best_type = RegionType.TABLE
        best = table_score
    if best_type is RegionType.TITLE and table_score > title_score and height >= 3:
        best_type = RegionType.TABLE
        best = table_score
    confidence = max(0.0, min(1.0, best))
    return best_type, evidence, confidence


def _header_footer_rows(
    cells: list[_CellFact], bbox: BoundingBox, region_type: RegionType
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if region_type is not RegionType.TABLE:
        return (), ()
    headers: list[int] = []
    footers: list[int] = []
    top = [c for c in cells if c.row == bbox.first_row]
    if _header_like(top):
        headers.append(bbox.first_row)
    bottom = [c for c in cells if c.row == bbox.last_row]
    if bottom and bbox.last_row != bbox.first_row:
        formula_ratio = sum(1 for c in bottom if c.formula) / len(bottom)
        bold_ratio = sum(1 for c in bottom if c.font_bold) / len(bottom)
        if formula_ratio >= 0.3 or bold_ratio >= 0.5:
            footers.append(bbox.last_row)
    return tuple(headers), tuple(footers)


def _stats_and_style(
    cells: list[_CellFact], bbox: BoundingBox
) -> tuple[RegionStatistics, RegionStyleProfile]:
    width = bbox.last_col - bbox.first_col + 1
    height = bbox.last_row - bbox.first_row + 1
    area = max(width * height, 1)
    occupied = len(cells)
    formula_count = sum(1 for c in cells if c.formula)
    kinds = {c.kind for c in cells}
    fills = [c.fill_color for c in cells if c.fill_color]
    fonts = [c.font_name for c in cells if c.font_name]
    bold_n = sum(1 for c in cells if c.font_bold)
    border_n = sum(1 for c in cells if c.bordered)
    dominant = Counter(fills).most_common(1)[0][0] if fills else None
    stats = RegionStatistics(
        cell_count=area,
        occupied_count=occupied,
        empty_ratio=max(0.0, 1.0 - occupied / area),
        formula_ratio=formula_count / max(occupied, 1),
        density=occupied / area,
        row_count=height,
        column_count=width,
        distinct_value_kinds=len(kinds),
    )
    profile = RegionStyleProfile(
        distinct_fill_colors=len(set(fills)),
        distinct_font_names=len(set(fonts)),
        bold_cell_ratio=bold_n / max(occupied, 1),
        bordered_cell_ratio=border_n / max(occupied, 1),
        dominant_fill_color=dominant,
    )
    return stats, profile


def _seed_structured_tables(
    ws: WorksheetInspection,
    regions: list[LogicalRegion],
    facts: dict[tuple[int, int], _CellFact],
    options: RegionDetectionOptions,
) -> list[LogicalRegion]:
    if not ws.tables:
        return regions
    seeded: list[LogicalRegion] = []
    absorbed_ids: set[str] = set()
    for idx, table in enumerate(ws.tables):
        parsed = _parse_range(table.reference)
        if parsed is None:
            continue
        r1, r2, c1, c2 = parsed
        bbox = BoundingBox(first_row=r1, last_row=r2, first_col=c1, last_col=c2)
        covered = [
            facts[key] for key in facts if r1 <= key[0] <= r2 and c1 <= key[1] <= c2
        ]
        if options.include_cell_coordinates:
            if covered:
                coords = tuple(sorted(c.coordinate for c in covered))
            else:
                coords = tuple(
                    _coord(r, c) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)
                )
        else:
            coords = ()
        cells_for_stats = covered or [
            _CellFact(
                coordinate=_coord(r, c),
                row=r,
                column=c,
                kind=CellValueKind.NULL,
                formula=None,
                has_comment=False,
                font_bold=False,
                font_name=None,
                font_size=None,
                fill_color=None,
                bordered=False,
            )
            for r in range(r1, r2 + 1)
            for c in range(c1, c2 + 1)
        ]
        stats, profile = _stats_and_style(cells_for_stats, bbox)
        headers = (r1,) if table.header_row_count else ()
        footers = (r2,) if table.totals_row_count else ()
        region_id = f"{ws.name}::structured::{table.name or idx}"
        evidence = (
            RegionEvidenceItem(
                "structured_table",
                1.0,
                f"Seeded from Excel table {table.name!r} ref={table.reference}",
            ),
        )
        seeded.append(
            LogicalRegion(
                id=region_id,
                sheet_name=ws.name,
                bounding_box=bbox,
                region_type=RegionType.TABLE,
                confidence=1.0,
                parent_id=None,
                children_ids=(),
                header_row_indices=headers,
                footer_row_indices=footers,
                cell_coordinates=coords,
                style_profile=profile,
                statistics=stats,
                evidence=evidence,
            )
        )
        for region in regions:
            rb = region.bounding_box
            if (
                rb.first_row >= r1
                and rb.last_row <= r2
                and rb.first_col >= c1
                and rb.last_col <= c2
            ):
                absorbed_ids.add(region.id)
    kept = [r for r in regions if r.id not in absorbed_ids]
    return seeded + kept


def _apply_nesting(
    regions: list[LogicalRegion],
    options: RegionDetectionOptions,
) -> list[LogicalRegion]:
    children: dict[str, list[str]] = defaultdict(list)
    parent_of: dict[str, str] = {}

    titles = [r for r in regions if r.region_type is RegionType.TITLE]
    tables = [r for r in regions if r.region_type is RegionType.TABLE]
    for title in titles:
        tb = title.bounding_box
        best: LogicalRegion | None = None
        best_gap = 10**9
        for table in tables:
            ub = table.bounding_box
            if ub.first_row <= tb.last_row:
                continue
            gap = ub.first_row - tb.last_row - 1
            if gap > options.nest_max_gap_rows:
                continue
            covers = tb.first_col <= ub.first_col and tb.last_col >= ub.last_col
            near = abs(tb.first_col - ub.first_col) <= options.nest_column_tolerance and abs(
                tb.last_col - ub.last_col
            ) <= options.nest_column_tolerance
            if not (covers or near):
                continue
            if gap < best_gap:
                best_gap = gap
                best = table
        if best is not None and best.id not in parent_of:
            parent_of[best.id] = title.id
            children[title.id].append(best.id)

    result: list[LogicalRegion] = []
    for region in regions:
        pid = parent_of.get(region.id)
        kids = tuple(children.get(region.id, ()))
        if pid == region.parent_id and kids == region.children_ids:
            result.append(region)
            continue
        result.append(
            LogicalRegion(
                id=region.id,
                sheet_name=region.sheet_name,
                bounding_box=region.bounding_box,
                region_type=region.region_type,
                confidence=region.confidence,
                parent_id=pid,
                children_ids=kids,
                header_row_indices=region.header_row_indices,
                footer_row_indices=region.footer_row_indices,
                cell_coordinates=region.cell_coordinates,
                style_profile=region.style_profile,
                statistics=region.statistics,
                evidence=region.evidence,
            )
        )
    return result


def _detect_sheet(
    ws: WorksheetInspection,
    options: RegionDetectionOptions,
) -> SheetRegions:
    facts = _build_facts(ws)
    components = _connected_components(facts, options)

    regions: list[LogicalRegion] = []
    sorted_components = sorted(
        components, key=lambda c: (min(x.row for x in c), min(x.column for x in c))
    )
    for idx, cells in enumerate(sorted_components):
        bbox = _bbox_of(cells)
        below_dense = any(
            _bbox_of(other).first_row > bbox.last_row
            and _bbox_of(other).first_row - bbox.last_row - 1 <= options.nest_max_gap_rows
            and (_bbox_of(other).last_row - _bbox_of(other).first_row)
            >= (bbox.last_row - bbox.first_row)
            and _bbox_of(other).last_col >= bbox.first_col
            and _bbox_of(other).first_col <= bbox.last_col
            for other in sorted_components
            if other is not cells
        )
        region_type, evidence, confidence = _classify(
            cells,
            bbox,
            merges=ws.merged_ranges,
            below_dense=below_dense,
        )
        headers, footers = _header_footer_rows(cells, bbox, region_type)
        stats, profile = _stats_and_style(cells, bbox)
        coords = (
            tuple(sorted(c.coordinate for c in cells))
            if options.include_cell_coordinates
            else ()
        )
        regions.append(
            LogicalRegion(
                id=f"{ws.name}::r{idx + 1}",
                sheet_name=ws.name,
                bounding_box=bbox,
                region_type=region_type,
                confidence=confidence,
                parent_id=None,
                children_ids=(),
                header_row_indices=headers,
                footer_row_indices=footers,
                cell_coordinates=coords,
                style_profile=profile,
                statistics=stats,
                evidence=tuple(evidence),
            )
        )

    regions = _seed_structured_tables(ws, regions, facts, options)
    regions = _apply_nesting(regions, options)
    regions.sort(key=lambda r: (r.bounding_box.first_row, r.bounding_box.first_col, r.id))
    return SheetRegions(sheet_name=ws.name, sheet_index=ws.index, regions=tuple(regions))


class HeuristicRegionDetector:
    """Pure application detector — never imports or opens Excel files."""

    def detect(
        self,
        inspection: WorkbookInspection,
        options: RegionDetectionOptions | None = None,
    ) -> RegionDetectionResult:
        opts = options or RegionDetectionOptions()
        sheets = tuple(_detect_sheet(ws, opts) for ws in inspection.worksheets)
        warnings: list[str] = []
        if inspection.completion_status.value == "partial":
            warnings.append(
                "Inspection was partial; region detection used observed cells only."
            )
        limitations = (
            "Region types are preliminary structural labels, not business semantics.",
            "Chart/image object geometry and pivot caches are out of scope for Phase 2B MVP.",
            "Detector consumes WorkbookInspection only; it never re-reads Excel bytes.",
        )
        return RegionDetectionResult(
            workbook_hash=inspection.file.content_hash,
            inspector_version=inspection.inspector_version,
            detector_version=DETECTOR_VERSION,
            regions_schema_version=REGIONS_SCHEMA_VERSION,
            sheets=sheets,
            warnings=tuple(warnings),
            limitations=limitations,
        )
