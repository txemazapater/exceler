"""Parse temporal values for ordering without locale guessing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum

from exceler.application.profiling.normalization import detect_date_pattern
from exceler.domain.workbook.enums import CellValueKind

_ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_ISO_DT_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?$")
_ISO_TIME_RE = re.compile(r"^(\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?$")
_SLASH_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


class TemporalKind(StrEnum):
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"


@dataclass(frozen=True)
class TemporalParseResult:
    original: str
    sort_key: datetime | None
    ambiguous: bool
    pattern: str | None
    kind: TemporalKind | None = None

    @property
    def ok(self) -> bool:
        return self.sort_key is not None and not self.ambiguous and self.kind is not None


def _dt(
    year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0
) -> datetime:
    return datetime(year, month, day, hour, minute, second)


def parse_temporal_text(text: str) -> TemporalParseResult:
    """Parse a textual date/datetime/time. Ambiguous day/month is not ordered."""
    raw = text.strip()
    match = _ISO_DATE_RE.match(raw)
    if match:
        y, m, d = (int(x) for x in match.groups())
        try:
            return TemporalParseResult(raw, _dt(y, m, d), False, "YYYY-MM-DD", TemporalKind.DATE)
        except ValueError:
            return TemporalParseResult(raw, None, False, None, None)

    match = _ISO_DT_RE.match(raw)
    if match:
        y_s, m_s, d_s, hh_s, mm_s, ss_s = match.groups()
        try:
            hour, minute, second = int(hh_s), int(mm_s), int(ss_s or 0)
            # Midnight datetime text is still datetime-shaped; keep DATETIME.
            return TemporalParseResult(
                raw,
                _dt(int(y_s), int(m_s), int(d_s), hour, minute, second),
                False,
                "YYYY-MM-DD HH:MM:SS",
                TemporalKind.DATETIME,
            )
        except ValueError:
            return TemporalParseResult(raw, None, False, None, None)

    match = _ISO_TIME_RE.match(raw)
    if match:
        hh_s, mm_s, ss_s = match.groups()
        try:
            # Anchor on a fixed date so time-only values remain comparable.
            return TemporalParseResult(
                raw,
                _dt(1970, 1, 1, int(hh_s), int(mm_s), int(ss_s or 0)),
                False,
                "HH:MM:SS",
                TemporalKind.TIME,
            )
        except ValueError:
            return TemporalParseResult(raw, None, False, None, None)

    match = _SLASH_RE.match(raw)
    if match:
        a, b, y = (int(x) for x in match.groups())
        pattern, ambiguous = detect_date_pattern(raw)
        if ambiguous or pattern is None:
            return TemporalParseResult(raw, None, True, pattern, TemporalKind.DATE)
        try:
            if pattern == "DD/MM/YYYY":
                return TemporalParseResult(raw, _dt(y, b, a), False, pattern, TemporalKind.DATE)
            if pattern == "MM/DD/YYYY":
                return TemporalParseResult(raw, _dt(y, a, b), False, pattern, TemporalKind.DATE)
        except ValueError:
            return TemporalParseResult(raw, None, False, None, None)
        return TemporalParseResult(raw, None, True, pattern, TemporalKind.DATE)

    return TemporalParseResult(raw, None, False, None, None)


def parse_temporal_value(
    *,
    kind: CellValueKind,
    original: str | None,
) -> TemporalParseResult | None:
    if not original:
        return None
    if kind is CellValueKind.DATE:
        parsed = parse_temporal_text(original[:10] if len(original) >= 10 else original)
        if parsed.sort_key is None:
            match = _ISO_DATE_RE.match(original.strip()[:10])
            if match:
                y, m, d = (int(x) for x in match.groups())
                try:
                    return TemporalParseResult(
                        original, _dt(y, m, d), False, "date", TemporalKind.DATE
                    )
                except ValueError:
                    return TemporalParseResult(original, None, False, None, None)
        return TemporalParseResult(
            original, parsed.sort_key, False, parsed.pattern or "date", TemporalKind.DATE
        )
    if kind is CellValueKind.DATETIME:
        parsed = parse_temporal_text(original.replace("T", " "))
        return TemporalParseResult(
            original,
            parsed.sort_key,
            False,
            parsed.pattern or "datetime",
            TemporalKind.DATETIME,
        )
    if kind is CellValueKind.TIME:
        parsed = parse_temporal_text(original)
        if parsed.sort_key is None and _ISO_TIME_RE.match(original.strip()):
            parsed = parse_temporal_text(original.strip())
        return TemporalParseResult(
            original, parsed.sort_key, False, parsed.pattern or "time", TemporalKind.TIME
        )
    if kind is CellValueKind.STRING:
        return parse_temporal_text(original)
    return None


def temporal_kind_compatible(selected_kind: TemporalKind, value_kind: TemporalKind) -> bool:
    """Cross-compatibility matrix for temporal logical types.

    - DATE accepts DATE only (not TIME; not DATETIME text/physical clock values).
    - DATETIME accepts DATE and DATETIME (date promotes).
    - TIME accepts TIME only.
    """
    if selected_kind is TemporalKind.DATETIME:
        return value_kind in {TemporalKind.DATE, TemporalKind.DATETIME}
    if selected_kind is TemporalKind.DATE:
        return value_kind is TemporalKind.DATE
    if selected_kind is TemporalKind.TIME:
        return value_kind is TemporalKind.TIME
    return False


def temporal_sort_key_from_parts(
    value_date: date | None = None,
    value_datetime: datetime | None = None,
    value_time: time | None = None,
) -> datetime | None:
    if value_datetime is not None:
        return value_datetime.replace(tzinfo=None)
    if value_date is not None:
        return datetime(value_date.year, value_date.month, value_date.day)
    if value_time is not None:
        return datetime(1970, 1, 1, value_time.hour, value_time.minute, value_time.second)
    return None
