"""Profile-driven segment selection."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from hhs_nofo_metrics.models import MetricSelectionRule, Segment, SelectionSummary


@dataclass(frozen=True, slots=True)
class SelectedText:
    text: str
    included_segments: tuple[Segment, ...]
    summary: SelectionSummary
    unable_reason: str | None = None


def select_metric_text(
    segments: tuple[Segment, ...], rule: MetricSelectionRule
) -> SelectedText:
    included: list[Segment] = []
    excluded: list[Segment] = []
    for segment in segments:
        if segment.inclusion_override is True:
            included.append(segment)
        elif segment.inclusion_override is False:
            excluded.append(segment)
        elif segment.role in rule.include_roles:
            included.append(segment)
        else:
            excluded.append(segment)

    unable_reason = None
    if rule.unknown_role_policy == "unable_to_calculate" and any(
        segment.role == "unknown" for segment in segments
    ):
        unable_reason = (
            "Profile cannot calculate this metric with unknown-role segments."
        )

    chunks: list[str] = []
    for segment in included:
        if chunks:
            chunks.append("\n\n" if segment.boundary_before == "page" else "\n")
        chunks.append(segment.text)
    included_counts = Counter(segment.role for segment in included)
    excluded_counts = Counter(segment.role for segment in excluded)
    return SelectedText(
        text="".join(chunks),
        included_segments=tuple(included),
        summary=SelectionSummary(
            included_segment_count=len(included),
            excluded_segment_count=len(excluded),
            included_role_counts=dict(included_counts),
            excluded_role_counts=dict(excluded_counts),
            unknown_role_policy=rule.unknown_role_policy,
        ),
        unable_reason=unable_reason,
    )
