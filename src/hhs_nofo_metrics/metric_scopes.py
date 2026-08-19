"""Resolve profile-declared metric rules into shared measurement scopes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from hhs_nofo_metrics.errors import ProfileError
from hhs_nofo_metrics.models import MetricProfile, MetricSelectionRule

DOCUMENT_CONTENT_SCOPE_ID: Final = "document_content"
READABILITY_SENTENCES_SCOPE_ID: Final = "readability_sentences"
SCOPE_METRIC_IDS: Final = {
    DOCUMENT_CONTENT_SCOPE_ID: ("word_count",),
    READABILITY_SENTENCES_SCOPE_ID: (
        "words_per_sentence",
        "characters_per_word",
        "flesch_reading_ease",
        "flesch_kincaid_grade_level",
        "passive_sentence_percentage",
    ),
}


@dataclass(frozen=True, slots=True)
class ProfileMetricScopes:
    """The two selection rules declared by one metric profile."""

    document_content: MetricSelectionRule
    readability_sentences: MetricSelectionRule


def _shared_rule(
    profile: MetricProfile, scope_id: str, metric_ids: tuple[str, ...]
) -> MetricSelectionRule:
    rules = {profile.metrics[metric_id] for metric_id in metric_ids}
    if len(rules) != 1:
        raise ProfileError(
            f"Measurement scope {scope_id!r} requires one shared selection rule "
            f"for metrics {list(metric_ids)}"
        )
    return next(iter(rules))


def resolve_profile_metric_scopes(profile: MetricProfile) -> ProfileMetricScopes:
    """Group explicit per-metric profile data into the engine's two scopes."""

    return ProfileMetricScopes(
        document_content=_shared_rule(
            profile,
            DOCUMENT_CONTENT_SCOPE_ID,
            SCOPE_METRIC_IDS[DOCUMENT_CONTENT_SCOPE_ID],
        ),
        readability_sentences=_shared_rule(
            profile,
            READABILITY_SENTENCES_SCOPE_ID,
            SCOPE_METRIC_IDS[READABILITY_SENTENCES_SCOPE_ID],
        ),
    )


__all__ = [
    "DOCUMENT_CONTENT_SCOPE_ID",
    "ProfileMetricScopes",
    "READABILITY_SENTENCES_SCOPE_ID",
    "SCOPE_METRIC_IDS",
    "resolve_profile_metric_scopes",
]
