from __future__ import annotations

import contextlib
import json
from io import StringIO
from pathlib import Path
from typing import Annotated

import typer

from exceler.application.workbook.serialization import inspection_to_dict
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


def register_workbook_commands(app: typer.Typer) -> None:
    workbook_app = typer.Typer(help="Workbook inspection commands (Phase 2A)")
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
