"""Logical type / identifier / categorical inference (Phase 2C)."""

from __future__ import annotations

from collections import Counter

from exceler.application.profiling.normalization import (
    NormalizedValue,
    detect_date_pattern,
    has_currency_signal,
    has_leading_zeroes,
    has_percentage_format,
    looks_code,
    looks_email,
    looks_percentage_text,
    looks_phone,
    looks_postal,
    looks_url,
    looks_uuid,
)
from exceler.domain.profiling.enums import (
    AnomalySeverity,
    AnomalyType,
    LogicalValueType,
)
from exceler.domain.profiling.models import (
    CategoricalAnalysis,
    ColumnAnomaly,
    IdentifierAnalysis,
    LogicalTypeInference,
    ProfilingEvidenceItem,
    TopValue,
    TypeCandidate,
)
from exceler.domain.profiling.options import ProfilingOptions
from exceler.domain.workbook.enums import CellValueKind


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _sample_sufficiency(n: int, options: ProfilingOptions) -> float:
    """Small homogeneous samples remain credible; large samples approach 1.0."""
    if n <= 0:
        return 0.0
    if n < options.minimum_rows_for_inference:
        return 0.35
    # Floor keeps high-compatibility columns above UNKNOWN (0.15) even for tiny corpora.
    return _clamp(0.6 + 0.4 * (n / options.sample_sufficiency_full_at))


def infer_logical_type(
    values: list[NormalizedValue],
    *,
    options: ProfilingOptions,
) -> LogicalTypeInference:
    content = [
        item for item in values if item.has_content and not item.is_formula and not item.is_error
    ]
    formulas = sum(1 for item in values if item.is_formula)
    n = len(content)
    sufficiency = _sample_sufficiency(n, options)
    evidence: list[ProfilingEvidenceItem] = []
    scores: dict[LogicalValueType, float] = {LogicalValueType.UNKNOWN: 0.15}

    if n == 0:
        selected = LogicalValueType.EMPTY if formulas == 0 else LogicalValueType.UNKNOWN
        conf = 0.4 if formulas else 0.9
        if formulas:
            evidence.append(
                ProfilingEvidenceItem(
                    "formula_only_column",
                    0.5,
                    "Column has formulas but no evaluated values",
                )
            )
        return LogicalTypeInference(
            selected_type=selected,
            confidence=conf,
            alternatives=(),
            evidence=tuple(evidence),
            incompatible_count=0,
        )

    kind_counts = Counter(item.kind for item in content)
    int_ratio = kind_counts[CellValueKind.INTEGER] / n
    dec_ratio = kind_counts[CellValueKind.DECIMAL] / n
    bool_ratio = kind_counts[CellValueKind.BOOLEAN] / n
    date_ratio = kind_counts[CellValueKind.DATE] / n
    dt_ratio = kind_counts[CellValueKind.DATETIME] / n
    time_ratio = kind_counts[CellValueKind.TIME] / n
    str_ratio = kind_counts[CellValueKind.STRING] / n

    def _physical_score(ratio: float, strong: float = 0.95, moderate: float = 0.72) -> float | None:
        if ratio >= options.high_compatibility_ratio:
            return strong * sufficiency
        if ratio >= options.moderate_compatibility_ratio:
            return moderate * sufficiency
        return None

    int_score = _physical_score(int_ratio)
    if int_score is not None:
        scores[LogicalValueType.INTEGER] = int_score
        evidence.append(
            ProfilingEvidenceItem(
                "physical_integer_ratio", int_ratio, f"integer_ratio={int_ratio:.3f}"
            )
        )
    dec_score = _physical_score(dec_ratio)
    if dec_score is not None:
        scores[LogicalValueType.DECIMAL] = dec_score
        evidence.append(
            ProfilingEvidenceItem(
                "physical_decimal_ratio", dec_ratio, f"decimal_ratio={dec_ratio:.3f}"
            )
        )
    num_ratio = int_ratio + dec_ratio
    if num_ratio >= options.moderate_compatibility_ratio and int_ratio and dec_ratio:
        scores[LogicalValueType.NUMBER] = 0.9 * sufficiency
        evidence.append(
            ProfilingEvidenceItem(
                "integer_decimal_promotion",
                num_ratio,
                "INTEGER+DECIMAL promoted to NUMBER",
            )
        )
    bool_score = _physical_score(bool_ratio)
    if bool_score is not None:
        scores[LogicalValueType.BOOLEAN] = bool_score
    date_score = _physical_score(date_ratio)
    if date_score is not None:
        scores[LogicalValueType.DATE] = date_score
    dt_score = _physical_score(dt_ratio)
    if dt_score is not None:
        scores[LogicalValueType.DATETIME] = dt_score
    time_score = _physical_score(time_ratio)
    if time_score is not None:
        scores[LogicalValueType.TIME] = time_score
    if (
        date_ratio
        and dt_ratio
        and date_ratio + dt_ratio >= options.moderate_compatibility_ratio
    ):
        scores[LogicalValueType.DATETIME] = max(
            scores.get(LogicalValueType.DATETIME, 0.0), 0.88 * sufficiency
        )

    # Format / text signals
    pct_fmt = sum(1 for item in content if has_percentage_format(item.number_format)) / n
    pct_text = (
        sum(1 for item in content if item.trimmed and looks_percentage_text(item.trimmed)) / n
    )
    if pct_fmt >= 0.5 or pct_text >= 0.5 or (pct_fmt + pct_text) >= 0.66:
        scores[LogicalValueType.PERCENTAGE] = 0.9 * sufficiency
        evidence.append(
            ProfilingEvidenceItem(
                "percentage_signal",
                max(pct_fmt, pct_text),
                "percentage format or % suffix",
            )
        )

    cur = sum(1 for item in content if has_currency_signal(item.original, item.number_format)) / n
    if cur >= 0.6:
        scores[LogicalValueType.CURRENCY] = 0.85 * sufficiency
        evidence.append(ProfilingEvidenceItem("currency_signal", cur, "currency symbol or format"))

    strings = [item for item in content if item.kind is CellValueKind.STRING and item.trimmed]
    if strings:
        sn = len(strings)
        uuid_r = sum(1 for item in strings if looks_uuid(item.trimmed or "")) / sn
        email_r = sum(1 for item in strings if looks_email(item.trimmed or "")) / sn
        url_r = sum(1 for item in strings if looks_url(item.trimmed or "")) / sn
        phone_r = sum(1 for item in strings if looks_phone(item.trimmed or "")) / sn
        postal_r = sum(1 for item in strings if looks_postal(item.trimmed or "")) / sn
        code_r = sum(1 for item in strings if looks_code(item.trimmed or "")) / sn
        leading0 = sum(1 for item in strings if has_leading_zeroes(item.trimmed or "")) / sn
        date_patterns = [
            detect_date_pattern(item.trimmed or "") for item in strings if item.trimmed
        ]
        date_ok = sum(1 for pattern, _ in date_patterns if pattern) / sn
        ambiguous = sum(1 for pattern, amb in date_patterns if amb) / sn

        if uuid_r >= 0.8:
            scores[LogicalValueType.UUID] = 0.95 * sufficiency
            scores[LogicalValueType.IDENTIFIER] = max(
                scores.get(LogicalValueType.IDENTIFIER, 0.0), 0.75 * sufficiency
            )
            scores[LogicalValueType.CODE] = max(
                scores.get(LogicalValueType.CODE, 0.0), 0.55 * sufficiency
            )
            evidence.append(ProfilingEvidenceItem("uuid_pattern_ratio", uuid_r, "UUID pattern"))
        if email_r >= 0.8:
            scores[LogicalValueType.EMAIL] = 0.93 * sufficiency
        if url_r >= 0.8:
            scores[LogicalValueType.URL] = 0.93 * sufficiency
        if phone_r >= 0.8:
            scores[LogicalValueType.PHONE] = 0.85 * sufficiency
        if postal_r >= 0.8:
            scores[LogicalValueType.POSTAL_CODE] = 0.8 * sufficiency
        if code_r >= 0.7 or leading0 >= 0.5:
            scores[LogicalValueType.CODE] = max(
                scores.get(LogicalValueType.CODE, 0.0), 0.8 * sufficiency
            )
            if leading0 >= 0.5:
                evidence.append(
                    ProfilingEvidenceItem(
                        "leading_zeroes", leading0, "leading zeroes preserved as text/code"
                    )
                )
        if date_ok >= options.moderate_compatibility_ratio:
            conf = 0.9 * sufficiency * (1.0 - 0.35 * ambiguous)
            scores[LogicalValueType.DATE] = max(scores.get(LogicalValueType.DATE, 0.0), conf)
            evidence.append(
                ProfilingEvidenceItem(
                    "textual_date_ratio", date_ok, f"parseable_date_ratio={date_ok:.3f}"
                )
            )
            if ambiguous >= 0.3:
                evidence.append(
                    ProfilingEvidenceItem(
                        "ambiguous_date_pattern",
                        ambiguous,
                        "ambiguous day/month ordering",
                    )
                )
        # TEXT is a weak fallback — keep score below specialized majority types.
        if str_ratio >= 0.8 and LogicalValueType.TEXT not in scores:
            scores[LogicalValueType.TEXT] = 0.45 * sufficiency

    if formulas / max(len(values), 1) >= 0.3:
        for key in list(scores):
            if key is not LogicalValueType.UNKNOWN:
                scores[key] *= 0.85
        evidence.append(
            ProfilingEvidenceItem(
                "formula_ratio_penalty",
                formulas / max(len(values), 1),
                "unevaluated formulas reduce type certainty",
            )
        )

    # Format-driven logical types outrank bare physical numeric when both apply.
    for specialized, bases in (
        (
            LogicalValueType.PERCENTAGE,
            (LogicalValueType.DECIMAL, LogicalValueType.NUMBER),
        ),
        (
            LogicalValueType.CURRENCY,
            (
                LogicalValueType.DECIMAL,
                LogicalValueType.NUMBER,
                LogicalValueType.INTEGER,
            ),
        ),
    ):
        if specialized in scores:
            ceiling = max((scores.get(base, 0.0) for base in bases), default=0.0)
            if ceiling > 0:
                scores[specialized] = max(scores[specialized], ceiling + 0.05)

    ranked = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0].value))
    selected_type, selected_conf = ranked[0]
    alternatives = tuple(
        TypeCandidate(type=type_, confidence=_clamp(conf))
        for type_, conf in ranked[1:4]
        if conf >= 0.3 and type_ is not selected_type
    )

    # Incompatible vs selected
    incompatible = _count_incompatible(content, selected_type)
    anomaly_penalty = _clamp(1.0 - (incompatible / max(n, 1)))
    confidence = _clamp(selected_conf * anomaly_penalty)
    return LogicalTypeInference(
        selected_type=selected_type,
        confidence=confidence,
        alternatives=alternatives,
        evidence=tuple(evidence),
        incompatible_count=incompatible,
    )


def _count_incompatible(content: list[NormalizedValue], selected: LogicalValueType) -> int:
    bad = 0
    for item in content:
        text = item.trimmed or ""
        if selected is LogicalValueType.INTEGER and item.kind not in {
            CellValueKind.INTEGER,
            CellValueKind.NULL,
        }:
            if item.kind is CellValueKind.STRING and text.isdigit():
                continue
            bad += 1
        elif selected is LogicalValueType.UUID and not looks_uuid(text):
            bad += 1
        elif selected is LogicalValueType.EMAIL and not looks_email(text):
            bad += 1
        elif selected is LogicalValueType.URL and not looks_url(text):
            bad += 1
        elif selected is LogicalValueType.DATE:
            if item.kind is CellValueKind.DATE:
                continue
            pattern, _ = detect_date_pattern(text) if text else (None, False)
            if not pattern:
                bad += 1
    return bad


def analyze_identifier(
    stats_unique_ratio: float,
    stats_non_null_ratio: float,
    logical: LogicalTypeInference,
    *,
    options: ProfilingOptions,
    leading_zero_ratio: float = 0.0,
) -> IdentifierAnalysis:
    reasons: list[str] = []
    warnings: list[str] = []
    score = 0.0
    if stats_unique_ratio >= options.identifier_unique_ratio:
        score += 0.45
        reasons.append("high_unique_ratio")
    if stats_non_null_ratio >= options.identifier_non_null_ratio:
        score += 0.35
        reasons.append("high_non_null_ratio")
    if logical.selected_type in {
        LogicalValueType.IDENTIFIER,
        LogicalValueType.UUID,
        LogicalValueType.CODE,
    }:
        score += 0.25
        reasons.append(f"logical_type_{logical.selected_type.value}")
    if leading_zero_ratio >= 0.3:
        score += 0.1
        reasons.append("leading_zeroes")
    if logical.selected_type in {
        LogicalValueType.CURRENCY,
        LogicalValueType.PERCENTAGE,
        LogicalValueType.BOOLEAN,
        LogicalValueType.TEXT,
    }:
        score -= 0.4
        warnings.append("logical_type_unlikely_for_identifier")
    if stats_unique_ratio < 0.9:
        warnings.append("duplicates_present")
    candidate = score >= 0.7
    return IdentifierAnalysis(
        is_candidate=candidate,
        confidence=_clamp(score),
        unique_ratio=stats_unique_ratio,
        non_null_ratio=stats_non_null_ratio,
        reasons=tuple(reasons),
        warnings=tuple(warnings),
    )


def analyze_categorical(
    counter: Counter[str],
    content_count: int,
    *,
    options: ProfilingOptions,
) -> CategoricalAnalysis:
    distinct = len(counter)
    ratio = distinct / max(content_count, 1)
    top = counter.most_common(options.top_values_limit)
    top_coverage = sum(count for _, count in top) / max(content_count, 1)
    has_repetition = content_count > distinct
    candidate = (
        0 < distinct <= options.categorical_max_distinct
        and content_count >= options.minimum_rows_for_inference
        and (
            ratio <= options.categorical_max_distinct_ratio
            or (distinct <= 5 and has_repetition)
        )
    )
    conf = 0.0
    if candidate:
        conf = _clamp((1.0 - ratio) * 0.6 + top_coverage * 0.4)
    return CategoricalAnalysis(
        is_categorical_candidate=candidate,
        confidence=conf,
        distinct_count=distinct,
        top_values=tuple(
            TopValue(value=value, count=count, ratio=count / max(content_count, 1))
            for value, count in top
        ),
        coverage_of_top_values=top_coverage,
    )


def collect_anomalies(
    values: list[NormalizedValue],
    selected: LogicalValueType,
    *,
    limit: int,
) -> tuple[ColumnAnomaly, ...]:
    anomalies: list[ColumnAnomaly] = []
    for item in values:
        if item.is_error:
            anomalies.append(
                ColumnAnomaly(
                    coordinate=item.coordinate,
                    original_value=item.original,
                    anomaly_type=AnomalyType.EXCEL_ERROR,
                    message="Excel error value",
                    expected_type=selected,
                    severity=AnomalySeverity.ERROR,
                )
            )
            continue
        if not item.has_content or item.is_formula:
            continue
        text = item.trimmed or item.original or ""
        mismatch = False
        if selected is LogicalValueType.DATE:
            if item.kind is CellValueKind.DATE:
                continue
            pattern, amb = detect_date_pattern(text)
            if not pattern:
                mismatch = True
            elif amb:
                anomalies.append(
                    ColumnAnomaly(
                        coordinate=item.coordinate,
                        original_value=item.original,
                        anomaly_type=AnomalyType.AMBIGUOUS_VALUE,
                        message="Ambiguous date ordering",
                        expected_type=selected,
                        severity=AnomalySeverity.WARNING,
                    )
                )
        elif selected is LogicalValueType.UUID and not looks_uuid(text):
            mismatch = True
        elif selected is LogicalValueType.EMAIL and not looks_email(text):
            mismatch = True
        elif selected is LogicalValueType.INTEGER:
            if item.kind not in {CellValueKind.INTEGER} and not text.isdigit():
                mismatch = True
        if mismatch:
            anomalies.append(
                ColumnAnomaly(
                    coordinate=item.coordinate,
                    original_value=item.original,
                    anomaly_type=AnomalyType.TYPE_MISMATCH,
                    message=f"Value incompatible with {selected.value}",
                    expected_type=selected,
                    severity=AnomalySeverity.WARNING,
                )
            )
        if len(anomalies) >= limit:
            break
    anomalies.sort(
        key=lambda item: (
            item.anomaly_type.value,
            item.coordinate or "",
            item.original_value or "",
        )
    )
    return tuple(anomalies)
