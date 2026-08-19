from __future__ import annotations

from dataclasses import replace

import pytest

from hhs_nofo_metrics import load_profile
from hhs_nofo_metrics.errors import ProfileError
from hhs_nofo_metrics.metric_scopes import (
    SCOPE_METRIC_IDS,
    resolve_profile_metric_scopes,
)
from hhs_nofo_metrics.models import MetricSelectionRule
from hhs_nofo_metrics.profile_store import list_profile_references


def test_bundled_profile_data_resolves_to_two_scopes() -> None:
    for reference in list_profile_references():
        profile = load_profile(reference)
        scopes = resolve_profile_metric_scopes(profile)

        assert scopes.document_content == profile.metrics["word_count"]
        assert scopes.readability_sentences == profile.metrics["words_per_sentence"]


def test_profile_may_intentionally_change_document_scope() -> None:
    profile = load_profile("hhs-nofo-fy27-html@0.4.0")
    metrics = dict(profile.metrics)
    metrics["word_count"] = MetricSelectionRule(
        include_roles=("body", "table", "list"),
        exclude_roles=(
            "heading",
            "cover",
            "table_of_contents",
            "instruction",
            "header",
            "footer",
            "navigation",
            "decorative",
            "unknown",
        ),
        unknown_role_policy="unable_to_calculate",
    )

    scopes = resolve_profile_metric_scopes(replace(profile, metrics=metrics))

    assert "heading" not in scopes.document_content.include_roles
    assert scopes.readability_sentences == profile.metrics["words_per_sentence"]


def test_readability_metrics_must_share_one_profile_rule() -> None:
    profile = load_profile("hhs-nofo-fy27-html@0.4.0")
    metrics = dict(profile.metrics)
    metrics["flesch_reading_ease"] = metrics["word_count"]

    with pytest.raises(ProfileError, match="requires one shared selection rule"):
        resolve_profile_metric_scopes(replace(profile, metrics=metrics))


def test_scope_mapping_covers_all_supported_metrics_once() -> None:
    mapped = [metric_id for values in SCOPE_METRIC_IDS.values() for metric_id in values]

    assert len(mapped) == len(set(mapped)) == 6
