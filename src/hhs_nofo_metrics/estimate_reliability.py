"""Versioned, source-free reliability evidence for provisional PDF estimates."""

from __future__ import annotations

from typing import Final

from hhs_nofo_metrics.models import (
    MethodIdentity,
    MetricReliability,
    MetricSensitivity,
)

RELIABILITY_METHOD_ID: Final = "hhs-pdf-estimate-reliability"
RELIABILITY_METHOD_VERSION: Final = "0.2.0"
RELIABILITY_METHOD_REFERENCE: Final = (
    f"{RELIABILITY_METHOD_ID}@{RELIABILITY_METHOD_VERSION}"
)

_HIGH_DELTA_LIMITS: Final = {
    "word_count": 0.5,
    "words_per_sentence": 0.5,
    "characters_per_word": 0.5,
    "flesch_reading_ease": 1.0,
    "flesch_kincaid_grade_level": 0.2,
    "passive_sentence_percentage": 0.5,
}
_MODERATE_DELTA_LIMITS: Final = {
    "word_count": 2.0,
    "words_per_sentence": 2.0,
    "characters_per_word": 2.0,
    "flesch_reading_ease": 3.0,
    "flesch_kincaid_grade_level": 0.5,
    "passive_sentence_percentage": 2.0,
}


def _delta_measure(metric_id: str, sensitivity: MetricSensitivity) -> float:
    if sensitivity.absolute_delta is None:
        return float("inf")
    if metric_id in {
        "flesch_reading_ease",
        "flesch_kincaid_grade_level",
        "passive_sentence_percentage",
    }:
        return float(sensitivity.absolute_delta)
    assert sensitivity.relative_delta_percent is not None
    return sensitivity.relative_delta_percent


def build_metric_reliability(
    *,
    metric_id: str,
    included_unknown_value: int | float,
    excluded_unknown_value: int | float | None,
    classification_coverage: float,
    unknown_segment_count: int,
    unknown_word_count: int,
    total_observed_word_count: int,
    failed_page_count: int,
    maximum_level: str | None = None,
    additional_reason_codes: tuple[str, ...] = (),
) -> MetricReliability:
    """Classify an estimate from explicit coverage and two policy scenarios."""

    absolute_delta = (
        abs(float(included_unknown_value) - float(excluded_unknown_value))
        if excluded_unknown_value is not None
        else None
    )
    denominator = (
        max(
            abs(float(included_unknown_value)),
            abs(float(excluded_unknown_value)),
            1.0,
        )
        if excluded_unknown_value is not None
        else None
    )
    relative_delta_percent = (
        absolute_delta / denominator * 100
        if absolute_delta is not None and denominator is not None
        else None
    )
    sensitivity = MetricSensitivity(
        included_unknown_value=included_unknown_value,
        excluded_unknown_value=excluded_unknown_value,
        absolute_delta=(
            round(absolute_delta, 4) if absolute_delta is not None else None
        ),
        relative_delta_percent=(
            round(relative_delta_percent, 4)
            if relative_delta_percent is not None
            else None
        ),
    )
    unknown_word_share = (
        unknown_word_count / total_observed_word_count
        if total_observed_word_count
        else 0.0
    )
    delta_measure = _delta_measure(metric_id, sensitivity)
    high_delta_limit = _HIGH_DELTA_LIMITS[metric_id]
    moderate_delta_limit = _MODERATE_DELTA_LIMITS[metric_id]

    if (
        excluded_unknown_value is None
        or failed_page_count
        or unknown_word_share > 0.02
        or delta_measure > moderate_delta_limit
    ):
        level = "low"
    elif unknown_word_share > 0.005 or delta_measure > high_delta_limit:
        level = "moderate"
    else:
        level = "high"

    level_order = {"low": 0, "moderate": 1, "high": 2}
    if maximum_level is not None:
        if maximum_level not in level_order:
            raise ValueError(f"unsupported reliability ceiling: {maximum_level}")
        if level_order[level] > level_order[maximum_level]:
            level = maximum_level

    reason_codes: list[str] = []
    if excluded_unknown_value is None:
        reason_codes.append("excluded_unknown_scenario_unusable")
    if failed_page_count:
        reason_codes.append("page_extraction_incomplete")
    if not unknown_segment_count:
        reason_codes.append("complete_resolved_role_scope")
    elif unknown_word_count == 0:
        reason_codes.append("unknown_segments_have_zero_word_units")
    else:
        reason_codes.append("unknown_segments_contain_word_units")
    if excluded_unknown_value is not None:
        if delta_measure <= high_delta_limit:
            reason_codes.append("unknown_policy_sensitivity_negligible")
        elif delta_measure <= moderate_delta_limit:
            reason_codes.append("unknown_policy_sensitivity_moderate")
        else:
            reason_codes.append("unknown_policy_sensitivity_material")
    reason_codes.extend(additional_reason_codes)

    return MetricReliability(
        level=level,
        method=MethodIdentity(
            status="configured",
            id=RELIABILITY_METHOD_ID,
            version=RELIABILITY_METHOD_VERSION,
        ),
        classification_coverage=classification_coverage,
        unknown_segment_count=unknown_segment_count,
        unknown_word_count=unknown_word_count,
        unknown_word_share=round(unknown_word_share, 6),
        failed_page_count=failed_page_count,
        sensitivity=sensitivity,
        reason_codes=tuple(reason_codes),
    )


__all__ = [
    "RELIABILITY_METHOD_ID",
    "RELIABILITY_METHOD_REFERENCE",
    "RELIABILITY_METHOD_VERSION",
    "build_metric_reliability",
]
