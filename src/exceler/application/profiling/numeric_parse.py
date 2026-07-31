"""Conservative numeric text parsing without assuming a locale."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from exceler.application.profiling.normalization import has_leading_zeroes

_CURRENCY_STRIP_RE = re.compile(r"[€$£¥]")
_SCI_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)[eE][+-]?\d+$")
_INT_RE = re.compile(r"^[+-]?\d+$")
_GROUPED_DOT_RE = re.compile(r"^[+-]?\d{1,3}(?:\.\d{3})+$")
_GROUPED_COMMA_RE = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})+$")
_SIMPLE_DOT_DEC_RE = re.compile(r"^[+-]?\d+\.\d+$")
_SIMPLE_COMMA_DEC_RE = re.compile(r"^[+-]?\d+,\d+$")


class NumericKind(StrEnum):
    INTEGER = "integer"
    DECIMAL = "decimal"


@dataclass(frozen=True)
class NumericParseResult:
    value: Decimal | None
    kind: NumericKind | None
    ambiguous: bool
    reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.value is not None and not self.ambiguous


_REJECT = NumericParseResult(None, None, False, "not_numeric")
_AMBIGUOUS = NumericParseResult(None, None, True, "ambiguous_separators")


def _strip_noise(text: str) -> tuple[str, bool]:
    """Remove currency symbols / percent; return (cleaned, is_percentage)."""
    raw = text.strip()
    is_pct = raw.endswith("%")
    if is_pct:
        raw = raw[:-1].strip()
    raw = _CURRENCY_STRIP_RE.sub("", raw)
    for code in ("USD", "EUR", "GBP"):
        raw = re.sub(rf"\b{code}\b", "", raw, flags=re.IGNORECASE)
    raw = raw.strip()
    return raw, is_pct


def _from_plain(token: str, *, is_pct: bool) -> NumericParseResult:
    try:
        value = Decimal(token)
    except InvalidOperation:
        return _REJECT
    if is_pct:
        value = value / Decimal(100)
        return NumericParseResult(value, NumericKind.DECIMAL, False, "percentage")
    if token.lstrip("+-").isdigit():
        return NumericParseResult(value, NumericKind.INTEGER, False, "integer")
    return NumericParseResult(value, NumericKind.DECIMAL, False, "decimal")


def parse_numeric_text(
    text: str,
    *,
    decimal_separator: str | None = None,
    allow_leading_zero_integers: bool = False,
) -> NumericParseResult:
    """Parse a numeric string without assuming en-US or European locale.

    Ambiguous forms such as ``1.234`` / ``1,234`` alone are not converted unless
    ``decimal_separator`` is provided by column-level consensus.
    """
    if not text or not text.strip():
        return _REJECT
    token, is_pct = _strip_noise(text)
    if not token:
        return _REJECT

    if _SCI_RE.match(token):
        return _from_plain(token.replace(",", ""), is_pct=is_pct)

    if _INT_RE.match(token):
        if has_leading_zeroes(token.lstrip("+-")) and not allow_leading_zero_integers:
            return NumericParseResult(None, None, False, "leading_zeroes")
        return _from_plain(token, is_pct=is_pct)

    if decimal_separator in {".", ","}:
        thousands = "," if decimal_separator == "." else "."
        normalized = token.replace(thousands, "").replace(decimal_separator, ".")
        if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", normalized):
            return _REJECT
        return _from_plain(normalized, is_pct=is_pct)

    # Both separators: the last one is the decimal separator (unambiguous).
    if "." in token and "," in token:
        last_dot = token.rfind(".")
        last_comma = token.rfind(",")
        if last_dot > last_comma:
            normalized = token.replace(",", "")
        else:
            normalized = token.replace(".", "").replace(",", ".")
        if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", normalized):
            return _REJECT
        return _from_plain(normalized, is_pct=is_pct)

    if _GROUPED_DOT_RE.match(token) or _GROUPED_COMMA_RE.match(token):
        # 1.234 or 1,234 — thousands vs decimal; needs column consensus.
        return _AMBIGUOUS

    if _SIMPLE_DOT_DEC_RE.match(token):
        _sign, _, frac = token.partition(".")
        # Exactly three fractional digits on a lone value is still ambiguous
        # (1.234 could be thousands), unless fraction length is not 3.
        if len(frac) == 3 and _sign.lstrip("+-").isdigit() and len(_sign.lstrip("+-")) <= 3:
            return _AMBIGUOUS
        return _from_plain(token, is_pct=is_pct)

    if _SIMPLE_COMMA_DEC_RE.match(token):
        _sign, _, frac = token.partition(",")
        if len(frac) == 3 and _sign.lstrip("+-").isdigit() and len(_sign.lstrip("+-")) <= 3:
            return _AMBIGUOUS
        # 1,5 / 12,34 — European decimal is the only plausible reading.
        if 1 <= len(frac) <= 2 or len(frac) > 3:
            return _from_plain(token.replace(",", "."), is_pct=is_pct)
        return _AMBIGUOUS

    return _REJECT


def infer_decimal_separator(texts: list[str]) -> str | None:
    """Infer a shared decimal separator from unambiguous column evidence.

    Returns ``'.'``, ``','``, or ``None`` when evidence is missing/conflicting.
    """
    votes: Counter[str] = Counter()
    for text in texts:
        token, _ = _strip_noise(text)
        if not token:
            continue
        if "." in token and "," in token:
            votes["." if token.rfind(".") > token.rfind(",") else ","] += 1
            continue
        if _SIMPLE_DOT_DEC_RE.match(token):
            _s, _, frac = token.partition(".")
            if len(frac) != 3:
                votes["."] += 1
            continue
        if _SIMPLE_COMMA_DEC_RE.match(token):
            _s, _, frac = token.partition(",")
            if len(frac) != 3:
                votes[","] += 1
            continue
    if not votes:
        return None
    if len(votes) > 1 and votes["."] == votes[","]:
        return None
    winner, count = votes.most_common(1)[0]
    if count <= 0:
        return None
    # Require clear majority when both appear.
    if len(votes) > 1 and count < sum(votes.values()) * 0.66:
        return None
    return winner
