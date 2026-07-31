from __future__ import annotations

import contextlib
import json
from io import StringIO
from pathlib import Path
from typing import Annotated

import typer

from exceler.application.profiling.profiler import DeterministicRegionProfiler
from exceler.application.profiling.serialization import profile_to_dict
from exceler.application.regions.heuristic_detector import HeuristicRegionDetector
from exceler.application.regions.serialization import regions_to_dict
from exceler.application.relationships.analyzer import DeterministicRelationshipAnalyzer
from exceler.application.relationships.serialization import relationships_to_dict
from exceler.application.workbook.serialization import inspection_to_dict
from exceler.domain.profiling.errors import ProfilingError
from exceler.domain.profiling.models import ProfilingResult
from exceler.domain.profiling.options import ProfilingOptions
from exceler.domain.regions.models import RegionDetectionResult
from exceler.domain.relationships.errors import RelationshipError
from exceler.domain.relationships.models import RelationshipAnalysisResult
from exceler.domain.relationships.options import RelationshipOptions
from exceler.domain.workbook.enums import InspectionCompletionStatus
from exceler.domain.workbook.errors import (
    EncryptedWorkbookError,
    InvalidWorkbookError,
    UnsupportedWorkbookFormatError,
    WorkbookAccessDeniedError,
    WorkbookInspectionError,
    WorkbookLimitExceededError,
    WorkbookNotFoundError,
)
from exceler.domain.workbook.models import WorkbookInspection, WorkbookInspectionOptions
from exceler.infrastructure.workbook.local_source import LocalWorkbookSource
from exceler.infrastructure.workbook.openpyxl_reader import OpenPyxlWorkbookReader

# Exit codes (documented in docs/workbook-inspection.md)
EXIT_OK = 0
EXIT_UNEXPECTED = 1
EXIT_INVALID_ARGS = 2
EXIT_UNSUPPORTED = 3
EXIT_NOT_FOUND = 4
EXIT_INVALID = 5
EXIT_LIMIT = 6
EXIT_PARTIAL = 7

PathArg = Annotated[Path, typer.Argument(exists=False, help="Path to .xlsx or .xlsm")]
FormatOpt = Annotated[str, typer.Option("--format", "-f", help="Output format: text|json")]
PrettyOpt = Annotated[bool, typer.Option("--pretty", help="Pretty-print JSON")]
OutputOpt = Annotated[
    Path | None, typer.Option("--output", "-o", help="Write output to a file instead of stdout")
]
MaxCellsOpt = Annotated[
    int | None,
    typer.Option("--max-cells", help="Override max_cells_observed safety limit"),
]
MaxScannedOpt = Annotated[
    int | None,
    typer.Option("--max-cells-scanned", help="Override max_cells_scanned safety limit"),
]
SampleSizeOpt = Annotated[
    int | None,
    typer.Option("--sample-size", help="Override profiling sample_size"),
]
TopValuesOpt = Annotated[
    int | None,
    typer.Option("--top-values-limit", help="Override profiling top_values_limit"),
]
IncludeUnknownOpt = Annotated[
    bool | None,
    typer.Option(
        "--include-unknown-regions/--no-include-unknown-regions",
        help="Profile UNKNOWN regions that meet minimum shape",
    ),
]


def _error_payload(code: str, message: str) -> dict[str, object]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _print_human(inspection: WorkbookInspection) -> None:
    typer.echo(f"Workbook: {inspection.file.file_name}")
    typer.echo(f"Format: {inspection.format.value}")
    typer.echo(f"Completion: {inspection.completion_status.value}")
    typer.echo(f"Worksheets: {inspection.worksheets_observed}")
    typer.echo(f"VBA project: {'yes' if inspection.has_vba_project else 'no'}")
    typer.echo(f"Cells observed: {inspection.cells_observed}")
    typer.echo(f"Cells scanned: {inspection.cells_scanned}")
    typer.echo(f"Duration: {inspection.duration_ms} ms")
    if inspection.truncation_reasons:
        typer.echo("Inspection completed partially.")
        for reason in inspection.truncation_reasons:
            loc = f" ({reason.location})" if reason.location else ""
            typer.echo(f"Reason: {reason.code.value}{loc}")
    typer.echo("")
    for ws in inspection.worksheets:
        typer.echo(f"[{ws.index}] {ws.name}")
        typer.echo(f"    Visibility: {ws.visibility.value}")
        typer.echo(f"    Dimension: {ws.declared_dimension or '-'}")
        typer.echo(f"    Cells observed: {ws.cells_observed}")
        typer.echo(f"    Cells scanned: {ws.cells_scanned}")
        typer.echo(f"    Tables: {len(ws.tables)}")
        typer.echo(f"    Merged ranges: {len(ws.merged_ranges)}")


def _print_regions_human(result: RegionDetectionResult) -> None:
    typer.echo(f"Workbook hash: {result.workbook_hash}")
    typer.echo(f"Detector: {result.detector_version}")
    typer.echo(f"Inspector: {result.inspector_version}")
    typer.echo(f"Schema: {result.regions_schema_version}")
    if result.warnings:
        for warning in result.warnings:
            typer.echo(f"Warning: {warning}")
    typer.echo("")
    for sheet in result.sheets:
        typer.echo(f"[{sheet.sheet_index}] {sheet.sheet_name} — {len(sheet.regions)} region(s)")
        for region in sheet.regions:
            box = region.bounding_box
            parent = f" parent={region.parent_id}" if region.parent_id else ""
            typer.echo(
                f"  {region.id}: {region.region_type.value} "
                f"r{box.first_row}-{box.last_row} c{box.first_col}-{box.last_col} "
                f"conf={region.confidence:.2f}{parent}"
            )


def _print_profile_human(result: ProfilingResult) -> None:
    typer.echo(f"Workbook hash: {result.workbook_hash}")
    typer.echo(f"Profiler: {result.profiler_version}")
    typer.echo(f"Schema: {result.profiling_schema_version}")
    if result.warnings:
        for warning in result.warnings:
            typer.echo(f"Warning: {warning}")
    typer.echo("")
    for sheet in result.sheets:
        typer.echo(f"[{sheet.sheet_index}] {sheet.sheet_name}")
        for region in sheet.region_profiles:
            typer.echo(
                f"  {region.region_id} ({region.region_type.value}) "
                f"status={region.profiling_status.value} cols={len(region.columns)}"
            )
            for col in region.columns:
                infer = col.logical_type_inference
                typer.echo(
                    f"    {col.column_letter} {col.effective_name}: "
                    f"{infer.selected_type.value} conf={infer.confidence:.2f} "
                    f"distinct={col.statistics.distinct_count}"
                )


def _print_relationships_human(result: RelationshipAnalysisResult) -> None:
    typer.echo(f"Workbook hash: {result.workbook_hash}")
    typer.echo(f"Engine: {result.relationship_engine_version}")
    typer.echo(f"Schema: {result.relationship_schema_version}")
    if result.warnings:
        for warning in result.warnings:
            typer.echo(f"Warning: {warning}")
    typer.echo("")
    for sheet in result.sheets:
        typer.echo(f"[{sheet.sheet_index}] {sheet.sheet_name}")
        for pk in sheet.primary_keys[:8]:
            typer.echo(
                f"  PK {pk.column.column_letter} {pk.column.effective_name}: "
                f"conf={pk.confidence:.2f} kind={pk.key_kind.value} "
                f"distinct_ratio={pk.statistics.distinct_ratio:.3f}"
            )
        for ck in sheet.composite_keys[:5]:
            names = "+".join(f"{c.column_letter}:{c.effective_name}" for c in ck.columns)
            typer.echo(f"  Composite {names}: conf={ck.confidence:.2f}")
    if result.foreign_keys:
        typer.echo("Foreign keys:")
        for fk in result.foreign_keys[:12]:
            typer.echo(
                f"  {fk.from_column.sheet_name}.{fk.from_column.effective_name} → "
                f"{fk.to_column.sheet_name}.{fk.to_column.effective_name} "
                f"incl={fk.inclusion_ratio:.3f} orphans={fk.orphan_count} "
                f"card={fk.cardinality.value} conf={fk.confidence:.2f}"
            )


def register_workbook_commands(app: typer.Typer) -> None:
    workbook_app = typer.Typer(help="Workbook inspection, regions, profiling, and relationships")
    app.add_typer(workbook_app, name="workbook")

    @workbook_app.command("inspect")
    def workbook_inspect(
        path: PathArg,
        format: FormatOpt = "text",
        pretty: PrettyOpt = False,
        output: OutputOpt = None,
        max_cells: MaxCellsOpt = None,
        max_cells_scanned: MaxScannedOpt = None,
    ) -> None:
        """Inspect a workbook factually (no table/type/key inference)."""
        as_json = format.lower() == "json"
        if format.lower() not in {"text", "json"}:
            payload = _error_payload("INVALID_ARGS", "format must be text or json")
            if as_json:
                typer.echo(json.dumps(payload))
            else:
                err = payload["error"]
                assert isinstance(err, dict)
                typer.echo(str(err["message"]))
            raise typer.Exit(EXIT_INVALID_ARGS)

        options = WorkbookInspectionOptions()
        if max_cells is not None or max_cells_scanned is not None:
            options = WorkbookInspectionOptions(
                include_empty_formatted_cells=options.include_empty_formatted_cells,
                include_comments=options.include_comments,
                include_hyperlinks=options.include_hyperlinks,
                include_external_links=options.include_external_links,
                max_worksheets=options.max_worksheets,
                max_cells_observed=(
                    max_cells if max_cells is not None else options.max_cells_observed
                ),
                max_cells_scanned=(
                    max_cells_scanned
                    if max_cells_scanned is not None
                    else options.max_cells_scanned
                ),
                max_file_size_bytes=options.max_file_size_bytes,
            )

        reader = OpenPyxlWorkbookReader()
        try:
            source = LocalWorkbookSource(path)
            inspection = reader.inspect(source, options)
        except WorkbookNotFoundError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_NOT_FOUND) from exc
        except WorkbookAccessDeniedError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_NOT_FOUND) from exc
        except UnsupportedWorkbookFormatError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_UNSUPPORTED) from exc
        except (InvalidWorkbookError, EncryptedWorkbookError) as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_INVALID) from exc
        except WorkbookLimitExceededError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_LIMIT) from exc
        except WorkbookInspectionError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_UNEXPECTED) from exc
        except Exception as exc:  # noqa: BLE001
            _emit_error(
                "UNEXPECTED_ERROR",
                "Unexpected inspection failure.",
                as_json=as_json,
                pretty=pretty,
                output=output,
            )
            raise typer.Exit(EXIT_UNEXPECTED) from exc

        if as_json:
            text = json.dumps(
                {"ok": True, **inspection_to_dict(inspection)},
                indent=2 if pretty else None,
                ensure_ascii=False,
            )
            _write(text, output)
        else:
            if output is not None:
                buf = StringIO()
                with contextlib.redirect_stdout(buf):
                    _print_human(inspection)
                _write(buf.getvalue(), output)
            else:
                _print_human(inspection)

        if inspection.completion_status is InspectionCompletionStatus.PARTIAL:
            raise typer.Exit(EXIT_PARTIAL)

    @workbook_app.command("regions")
    def workbook_regions(
        path: PathArg,
        format: FormatOpt = "text",
        pretty: PrettyOpt = False,
        output: OutputOpt = None,
        max_cells: MaxCellsOpt = None,
        max_cells_scanned: MaxScannedOpt = None,
    ) -> None:
        """Inspect then detect logical regions (Phase 2B; no Excel re-read in detector)."""
        as_json = format.lower() == "json"
        if format.lower() not in {"text", "json"}:
            payload = _error_payload("INVALID_ARGS", "format must be text or json")
            if as_json:
                typer.echo(json.dumps(payload))
            else:
                err = payload["error"]
                assert isinstance(err, dict)
                typer.echo(str(err["message"]))
            raise typer.Exit(EXIT_INVALID_ARGS)

        options = WorkbookInspectionOptions()
        if max_cells is not None or max_cells_scanned is not None:
            options = WorkbookInspectionOptions(
                include_empty_formatted_cells=options.include_empty_formatted_cells,
                include_comments=options.include_comments,
                include_hyperlinks=options.include_hyperlinks,
                include_external_links=options.include_external_links,
                max_worksheets=options.max_worksheets,
                max_cells_observed=(
                    max_cells if max_cells is not None else options.max_cells_observed
                ),
                max_cells_scanned=(
                    max_cells_scanned
                    if max_cells_scanned is not None
                    else options.max_cells_scanned
                ),
                max_file_size_bytes=options.max_file_size_bytes,
            )

        reader = OpenPyxlWorkbookReader()
        detector = HeuristicRegionDetector()
        try:
            source = LocalWorkbookSource(path)
            inspection = reader.inspect(source, options)
            result = detector.detect(inspection)
        except WorkbookNotFoundError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_NOT_FOUND) from exc
        except WorkbookAccessDeniedError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_NOT_FOUND) from exc
        except UnsupportedWorkbookFormatError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_UNSUPPORTED) from exc
        except (InvalidWorkbookError, EncryptedWorkbookError) as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_INVALID) from exc
        except WorkbookLimitExceededError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_LIMIT) from exc
        except WorkbookInspectionError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_UNEXPECTED) from exc
        except Exception as exc:  # noqa: BLE001
            _emit_error(
                "UNEXPECTED_ERROR",
                "Unexpected region detection failure.",
                as_json=as_json,
                pretty=pretty,
                output=output,
            )
            raise typer.Exit(EXIT_UNEXPECTED) from exc

        if as_json:
            text = json.dumps(
                {"ok": True, **regions_to_dict(result)},
                indent=2 if pretty else None,
                ensure_ascii=False,
            )
            _write(text, output)
        else:
            if output is not None:
                buf = StringIO()
                with contextlib.redirect_stdout(buf):
                    _print_regions_human(result)
                _write(buf.getvalue(), output)
            else:
                _print_regions_human(result)

        if inspection.completion_status is InspectionCompletionStatus.PARTIAL:
            raise typer.Exit(EXIT_PARTIAL)

    @workbook_app.command("profile")
    def workbook_profile(
        path: PathArg,
        format: FormatOpt = "text",
        pretty: PrettyOpt = False,
        output: OutputOpt = None,
        max_cells: MaxCellsOpt = None,
        max_cells_scanned: MaxScannedOpt = None,
        sample_size: SampleSizeOpt = None,
        top_values_limit: TopValuesOpt = None,
        include_unknown_regions: IncludeUnknownOpt = None,
    ) -> None:
        """Inspect, detect regions, then profile columns (Phase 2C; no Excel re-read)."""
        as_json = format.lower() == "json"
        if format.lower() not in {"text", "json"}:
            payload = _error_payload("INVALID_ARGS", "format must be text or json")
            if as_json:
                typer.echo(json.dumps(payload))
            else:
                err = payload["error"]
                assert isinstance(err, dict)
                typer.echo(str(err["message"]))
            raise typer.Exit(EXIT_INVALID_ARGS)

        inspect_options = WorkbookInspectionOptions()
        if max_cells is not None or max_cells_scanned is not None:
            inspect_options = WorkbookInspectionOptions(
                include_empty_formatted_cells=inspect_options.include_empty_formatted_cells,
                include_comments=inspect_options.include_comments,
                include_hyperlinks=inspect_options.include_hyperlinks,
                include_external_links=inspect_options.include_external_links,
                max_worksheets=inspect_options.max_worksheets,
                max_cells_observed=(
                    max_cells if max_cells is not None else inspect_options.max_cells_observed
                ),
                max_cells_scanned=(
                    max_cells_scanned
                    if max_cells_scanned is not None
                    else inspect_options.max_cells_scanned
                ),
                max_file_size_bytes=inspect_options.max_file_size_bytes,
            )

        base_prof = ProfilingOptions()
        profile_options = ProfilingOptions(
            include_unknown_regions=(
                include_unknown_regions
                if include_unknown_regions is not None
                else base_prof.include_unknown_regions
            ),
            minimum_region_confidence=base_prof.minimum_region_confidence,
            minimum_rows_for_inference=base_prof.minimum_rows_for_inference,
            sample_size=sample_size if sample_size is not None else base_prof.sample_size,
            top_values_limit=(
                top_values_limit if top_values_limit is not None else base_prof.top_values_limit
            ),
            anomaly_sample_limit=base_prof.anomaly_sample_limit,
            max_distinct_values_tracked=base_prof.max_distinct_values_tracked,
            max_values_profiled_per_column=base_prof.max_values_profiled_per_column,
            trim_strings_for_analysis=base_prof.trim_strings_for_analysis,
            case_sensitive_cardinality=base_prof.case_sensitive_cardinality,
            exclude_header_rows=base_prof.exclude_header_rows,
            exclude_footer_rows=base_prof.exclude_footer_rows,
            high_compatibility_ratio=base_prof.high_compatibility_ratio,
            identifier_unique_ratio=base_prof.identifier_unique_ratio,
            identifier_non_null_ratio=base_prof.identifier_non_null_ratio,
            categorical_max_distinct=base_prof.categorical_max_distinct,
            categorical_max_distinct_ratio=base_prof.categorical_max_distinct_ratio,
            sample_sufficiency_full_at=base_prof.sample_sufficiency_full_at,
            min_unknown_region_rows=base_prof.min_unknown_region_rows,
            min_unknown_region_cols=base_prof.min_unknown_region_cols,
        )

        reader = OpenPyxlWorkbookReader()
        detector = HeuristicRegionDetector()
        profiler = DeterministicRegionProfiler()
        try:
            source = LocalWorkbookSource(path)
            inspection = reader.inspect(source, inspect_options)
            regions = detector.detect(inspection)
            result = profiler.profile(inspection, regions, profile_options)
        except WorkbookNotFoundError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_NOT_FOUND) from exc
        except WorkbookAccessDeniedError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_NOT_FOUND) from exc
        except UnsupportedWorkbookFormatError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_UNSUPPORTED) from exc
        except (InvalidWorkbookError, EncryptedWorkbookError) as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_INVALID) from exc
        except WorkbookLimitExceededError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_LIMIT) from exc
        except ProfilingError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_INVALID) from exc
        except WorkbookInspectionError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_UNEXPECTED) from exc
        except Exception as exc:  # noqa: BLE001
            _emit_error(
                "UNEXPECTED_ERROR",
                "Unexpected profiling failure.",
                as_json=as_json,
                pretty=pretty,
                output=output,
            )
            raise typer.Exit(EXIT_UNEXPECTED) from exc

        if as_json:
            text = json.dumps(
                {"ok": True, **profile_to_dict(result)},
                indent=2 if pretty else None,
                ensure_ascii=False,
            )
            _write(text, output)
        else:
            if output is not None:
                buf = StringIO()
                with contextlib.redirect_stdout(buf):
                    _print_profile_human(result)
                _write(buf.getvalue(), output)
            else:
                _print_profile_human(result)

        if inspection.completion_status is InspectionCompletionStatus.PARTIAL:
            raise typer.Exit(EXIT_PARTIAL)

    @workbook_app.command("relationships")
    def workbook_relationships(
        path: PathArg,
        format: FormatOpt = "text",
        pretty: PrettyOpt = False,
        output: OutputOpt = None,
        max_cells: MaxCellsOpt = None,
        max_cells_scanned: MaxScannedOpt = None,
    ) -> None:
        """Inspect, detect regions, profile, then analyze keys/relationships (Phase 2D)."""
        as_json = format.lower() == "json"
        if format.lower() not in {"text", "json"}:
            payload = _error_payload("INVALID_ARGS", "format must be text or json")
            if as_json:
                typer.echo(json.dumps(payload))
            else:
                err = payload["error"]
                assert isinstance(err, dict)
                typer.echo(str(err["message"]))
            raise typer.Exit(EXIT_INVALID_ARGS)

        inspect_options = WorkbookInspectionOptions()
        if max_cells is not None or max_cells_scanned is not None:
            inspect_options = WorkbookInspectionOptions(
                include_empty_formatted_cells=inspect_options.include_empty_formatted_cells,
                include_comments=inspect_options.include_comments,
                include_hyperlinks=inspect_options.include_hyperlinks,
                include_external_links=inspect_options.include_external_links,
                max_worksheets=inspect_options.max_worksheets,
                max_cells_observed=(
                    max_cells if max_cells is not None else inspect_options.max_cells_observed
                ),
                max_cells_scanned=(
                    max_cells_scanned
                    if max_cells_scanned is not None
                    else inspect_options.max_cells_scanned
                ),
                max_file_size_bytes=inspect_options.max_file_size_bytes,
            )

        reader = OpenPyxlWorkbookReader()
        detector = HeuristicRegionDetector()
        profiler = DeterministicRegionProfiler()
        analyzer = DeterministicRelationshipAnalyzer()
        try:
            source = LocalWorkbookSource(path)
            inspection = reader.inspect(source, inspect_options)
            regions = detector.detect(inspection)
            profiling = profiler.profile(inspection, regions, ProfilingOptions())
            result = analyzer.analyze(inspection, regions, profiling, RelationshipOptions())
        except WorkbookNotFoundError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_NOT_FOUND) from exc
        except WorkbookAccessDeniedError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_NOT_FOUND) from exc
        except UnsupportedWorkbookFormatError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_UNSUPPORTED) from exc
        except (InvalidWorkbookError, EncryptedWorkbookError) as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_INVALID) from exc
        except WorkbookLimitExceededError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_LIMIT) from exc
        except (ProfilingError, RelationshipError) as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_INVALID) from exc
        except WorkbookInspectionError as exc:
            _emit_error(exc.code, exc.message, as_json=as_json, pretty=pretty, output=output)
            raise typer.Exit(EXIT_UNEXPECTED) from exc
        except Exception as exc:  # noqa: BLE001
            _emit_error(
                "UNEXPECTED_ERROR",
                "Unexpected relationship analysis failure.",
                as_json=as_json,
                pretty=pretty,
                output=output,
            )
            raise typer.Exit(EXIT_UNEXPECTED) from exc

        if as_json:
            text = json.dumps(
                {"ok": True, **relationships_to_dict(result)},
                indent=2 if pretty else None,
                ensure_ascii=False,
            )
            _write(text, output)
        else:
            if output is not None:
                buf = StringIO()
                with contextlib.redirect_stdout(buf):
                    _print_relationships_human(result)
                _write(buf.getvalue(), output)
            else:
                _print_relationships_human(result)

        if inspection.completion_status is InspectionCompletionStatus.PARTIAL:
            raise typer.Exit(EXIT_PARTIAL)


def _emit_error(
    code: str,
    message: str,
    *,
    as_json: bool,
    pretty: bool,
    output: Path | None,
) -> None:
    if as_json:
        text = json.dumps(
            _error_payload(code, message),
            indent=2 if pretty else None,
            ensure_ascii=False,
        )
        _write(text, output)
    else:
        _write(f"{code}: {message}", output)


def _write(text: str, output: Path | None) -> None:
    if output is None:
        typer.echo(text)
    else:
        output.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
