"""Analytic string/value normalization for profiling (does not mutate originals)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from exceler.domain.workbook.enums import CellValueKind
from exceler.domain.workbook.models import CellInspection, CellValue

_WS_RE = re.compile(r"\s+")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_RE = re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE)
_PHONE_RE = re.compile(r"^\+?[\d\s().-]{7,20}$")
_POSTAL_RE = re.compile(r"^\d{4,10}(-\d{3,4})?$|^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$", re.I)
_CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,31}$")
_PCT_RE = re.compile(r"^-?\d+(\.\d+)?\s*%$")
_CURRENCY_SYM_RE = re.compile(r"(€|\$|£|¥|USD|EUR|GBP)", re.I)
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_DT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?$")
_DMY_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_LEADING_ZERO_INT_RE = re.compile(r"^0\d+$")


@dataclass(frozen=True)
class NormalizedValue:
    original: str | None
    trimmed: str | None
    kind: CellValueKind
    is_null: bool
    is_blank_string: bool
    is_whitespace_only: bool
    is_formula: bool
    is_error: bool
    has_content: bool
    coordinate: str | None
    number_format: str | None


def cell_value_original(value: CellValue) -> str | None:
    if value.kind is CellValueKind.NULL:
        return None
    if value.text is not None:
        return value.text
    if value.integer is not None:
        return str(value.integer)
    if value.decimal is not None:
        return value.decimal
    if value.boolean is not None:
        return "TRUE" if value.boolean else "FALSE"
    if value.date is not None:
        return value.date
    if value.datetime is not None:
        return value.datetime
    if value.time is not None:
        return value.time
    if value.error is not None:
        return value.error
    return None


def normalize_cell(
    cell: CellInspection | None,
    *,
    coordinate: str | None = None,
    trim: bool = True,
) -> NormalizedValue:
    if cell is None:
        return NormalizedValue(
            original=None,
            trimmed=None,
            kind=CellValueKind.NULL,
            is_null=True,
            is_blank_string=False,
            is_whitespace_only=False,
            is_formula=False,
            is_error=False,
            has_content=False,
            coordinate=coordinate,
            number_format=None,
        )
    is_formula = cell.formula is not None
    is_error = cell.value.kind is CellValueKind.ERROR
    original = cell.formula if is_formula else cell_value_original(cell.value)
    if is_formula:
        # Formula present: content without evaluated value.
        return NormalizedValue(
            original=original,
            trimmed=original.strip() if original and trim else original,
            kind=CellValueKind.NULL,
            is_null=True,
            is_blank_string=False,
            is_whitespace_only=False,
            is_formula=True,
            is_error=False,
            has_content=True,
            coordinate=cell.coordinate,
            number_format=cell.number_format,
        )
    if cell.value.kind is CellValueKind.NULL:
        return NormalizedValue(
            original=None,
            trimmed=None,
            kind=CellValueKind.NULL,
            is_null=True,
            is_blank_string=False,
            is_whitespace_only=False,
            is_formula=False,
            is_error=False,
            has_content=False,
            coordinate=cell.coordinate,
            number_format=cell.number_format,
        )
    text = original
    trimmed = text.strip() if text is not None and trim else text
    is_blank = text == ""
    is_ws = bool(text is not None and text != "" and trimmed == "")
    return NormalizedValue(
        original=text,
        trimmed=trimmed,
        kind=cell.value.kind,
        is_null=False,
        is_blank_string=is_blank,
        is_whitespace_only=is_ws,
        is_formula=False,
        is_error=is_error,
        has_content=not is_blank and not is_ws and not is_error,
        coordinate=cell.coordinate,
        number_format=cell.number_format,
    )


def abstract_pattern(text: str) -> str:
    out: list[str] = []
    for ch in text:
        if ch.isalpha():
            out.append("A" if ch.isupper() else "a")
        elif ch.isdigit():
            out.append("9")
        else:
            out.append(ch)
    # Collapse runs of same class letter for stability
    collapsed: list[str] = []
    for ch in out:
        if collapsed and collapsed[-1] == ch and ch in {"A", "a", "9"}:
            continue
        # Keep up to 4 of same for length signal
        if collapsed and ch in {"A", "a", "9"} and collapsed[-1] == ch and collapsed.count(ch) >= 4:
            continue
        collapsed.append(ch)
    return "".join(collapsed)


def looks_uuid(text: str) -> bool:
    return bool(_UUID_RE.match(text))


def looks_email(text: str) -> bool:
    return bool(_EMAIL_RE.match(text)) and len(text) <= 254


def looks_url(text: str) -> bool:
    return bool(_URL_RE.match(text))


def looks_phone(text: str) -> bool:
    digits = sum(ch.isdigit() for ch in text)
    return bool(_PHONE_RE.match(text)) and 7 <= digits <= 15


def looks_postal(text: str) -> bool:
    return bool(_POSTAL_RE.match(text.strip()))


def looks_code(text: str) -> bool:
    if not _CODE_RE.match(text):
        return False
    if " " in text.strip():
        return False
    return any(ch.isdigit() for ch in text) or "-" in text or "/" in text


def looks_percentage_text(text: str) -> bool:
    return bool(_PCT_RE.match(text.strip()))


def has_currency_signal(text: str | None, number_format: str | None) -> bool:
    fmt = (number_format or "").lower()
    if any(token in fmt for token in ("$", "€", "£", "¥", "usd", "eur", "gbp")):
        return True
    if text and _CURRENCY_SYM_RE.search(text):
        return True
    return False


def has_percentage_format(number_format: str | None) -> bool:
    return number_format is not None and "%" in number_format


def has_leading_zeroes(text: str) -> bool:
    return bool(_LEADING_ZERO_INT_RE.match(text))


def detect_date_pattern(text: str) -> tuple[str | None, bool]:
    """Return (pattern, ambiguous)."""
    if _ISO_DATE_RE.match(text):
        return "YYYY-MM-DD", False
    if _ISO_DT_RE.match(text):
        return "YYYY-MM-DD HH:MM:SS", False
    match = _DMY_RE.match(text)
    if match:
        a, b = int(match.group(1)), int(match.group(2))
        if a > 12 and b <= 12:
            return "DD/MM/YYYY", False
        if b > 12 and a <= 12:
            return "MM/DD/YYYY", False
        return "DD/MM/YYYY|MM/DD/YYYY", True
    return None, False
