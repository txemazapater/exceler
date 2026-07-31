"""Build column profiles from inspection cells + region contract."""

from __future__ import annotations

from exceler.application.profiling.inference import (
    analyze_categorical,
    analyze_identifier,
    collect_anomalies,
    infer_logical_type,
)
from exceler.application.profiling.normalization import (
    NormalizedValue,
    has_leading_zeroes,
    normalize_cell,
)
from exceler.application.profiling.statistics import (
    build_column_statistics,
    build_physical_distribution,
)
from exceler.domain.profiling.models import (
    ColumnProfile,
    ProfilingEvidenceItem,
    SampleValue,
)
from exceler.domain.profiling.options import ProfilingOptions
from exceler.domain.regions.models import LogicalRegion
from exceler.domain.workbook.enums import CellValueKind
from exceler.domain.workbook.models import CellInspection


def _col_letter(index: int) -> str:
    n = index
    letters: list[str] = []
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters.append(chr(ord("A") + rem))
    return "".join(reversed(letters))


def _coord(row: int, col: int) -> str:
    return f"{_col_letter(col)}{row}"


def data_row_indices(region: LogicalRegion, options: ProfilingOptions) -> list[int]:
    box = region.bounding_box
    headers = set(region.header_row_indices) if options.exclude_header_rows else set()
    footers = set(region.footer_row_indices) if options.exclude_footer_rows else set()
    return [
        row
        for row in range(box.first_row, box.last_row + 1)
        if row not in headers and row not in footers
    ]


def build_stable_column_id(
    workbook_hash: str, sheet_name: str, region_id: str, column_index: int
) -> str:
    return f"{workbook_hash[:12]}::{sheet_name}::{region_id}::c{column_index}"


def _sample_values(
    values: list[NormalizedValue],
    anomalies_coords: set[str | None],
    *,
    sample_size: int,
) -> tuple[SampleValue, ...]:
    if not values:
        return ()
    picks: list[SampleValue] = []
    seen: set[tuple[str | None, str | None]] = set()

    def add(item: NormalizedValue, role: str) -> None:
        key = (item.coordinate, item.original)
        if key in seen:
            return
        seen.add(key)
        picks.append(
            SampleValue(
                coordinate=item.coordinate,
                original=item.original,
                kind=item.kind if not item.is_formula else None,
                role=role,
            )
        )

    add(values[0], "first")
    add(values[-1], "last")
    if len(values) > 2:
        step = max(1, len(values) // max(sample_size // 2, 1))
        for idx in range(step, len(values) - 1, step):
            add(values[idx], "middle")
            if len(picks) >= sample_size:
                break
    for item in values:
        if item.coordinate in anomalies_coords:
            add(item, "anomaly")
        if len(picks) >= sample_size:
            break
    picks.sort(key=lambda sample: (sample.role, sample.coordinate or "", sample.original or ""))
    return tuple(picks[:sample_size])


def profile_column(
    *,
    workbook_hash: str,
    sheet_name: str,
    region: LogicalRegion,
    column_index: int,
    cell_index: dict[tuple[int, int], CellInspection],
    options: ProfilingOptions,
) -> ColumnProfile:
    box = region.bounding_box
    letter = _col_letter(column_index)
    header_rows = list(region.header_row_indices) if options.exclude_header_rows else []
    footer_rows = list(region.footer_row_indices) if options.exclude_footer_rows else []
    header_values: list[str] = []
    for row in header_rows:
        cell = cell_index.get((row, column_index))
        norm = normalize_cell(cell, coordinate=_coord(row, column_index), trim=True)
        if norm.trimmed:
            header_values.append(norm.trimmed)
    footer_values: list[str] = []
    for row in footer_rows:
        cell = cell_index.get((row, column_index))
        norm = normalize_cell(cell, coordinate=_coord(row, column_index), trim=True)
        if norm.original is not None:
            footer_values.append(norm.original)

    rows = data_row_indices(region, options)
    data_values: list[NormalizedValue] = []
    observed = 0
    unobserved = 0
    for row in rows:
        cell = cell_index.get((row, column_index))
        coord = _coord(row, column_index)
        if cell is None:
            unobserved += 1
            data_values.append(
                normalize_cell(None, coordinate=coord, trim=options.trim_strings_for_analysis)
            )
        else:
            observed += 1
            data_values.append(
                normalize_cell(cell, coordinate=coord, trim=options.trim_strings_for_analysis)
            )

    stats, counter = build_column_statistics(
        data_values,
        options=options,
        observed_count=observed,
        unobserved_count=unobserved,
    )
    physical = build_physical_distribution(data_values)
    logical = infer_logical_type(data_values, options=options)

    non_null_ratio = stats.content_count / max(stats.total_row_count, 1)
    leading0 = 0.0
    strings = [item for item in data_values if item.kind is CellValueKind.STRING and item.trimmed]
    if strings:
        leading0 = sum(1 for item in strings if has_leading_zeroes(item.trimmed or "")) / len(
            strings
        )

    identifier = analyze_identifier(
        stats.unique_ratio,
        non_null_ratio,
        logical,
        options=options,
        leading_zero_ratio=leading0,
    )
    categorical = analyze_categorical(counter, stats.content_count, options=options)
    anomalies = collect_anomalies(
        data_values, logical.selected_type, limit=options.anomaly_sample_limit
    )
    sample = _sample_values(
        data_values,
        {item.coordinate for item in anomalies},
        sample_size=options.sample_size,
    )

    if header_values:
        effective = " / ".join(header_values)
    else:
        effective = f"Column {letter}"

    evidence = list(logical.evidence)
    evidence.append(
        ProfilingEvidenceItem(
            "column_shape",
            0.1,
            f"rows={len(rows)} observed={observed} content={stats.content_count}",
            details={"column_index": column_index, "bbox": box.to_dict()},
        )
    )

    return ColumnProfile(
        id=build_stable_column_id(workbook_hash, sheet_name, region.id, column_index),
        region_id=region.id,
        sheet_name=sheet_name,
        column_index=column_index,
        column_letter=letter,
        header_values=tuple(header_values),
        effective_name=effective,
        statistics=stats,
        physical_type_distribution=physical,
        logical_type_inference=logical,
        identifier_analysis=identifier,
        categorical_analysis=categorical,
        anomalies=anomalies,
        sample=sample,
        evidence=tuple(evidence),
        footer_values=tuple(footer_values),
    )
