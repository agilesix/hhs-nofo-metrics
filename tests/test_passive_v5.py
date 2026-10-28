"""Invented examples for the opt-in definition-modifier candidate."""

import pytest

from hhs_nofo_metrics.methods import passive_voice_v4 as released
from hhs_nofo_metrics.methods import passive_voice_v5 as candidate
from hhs_nofo_metrics.profile_store import list_profile_references, load_profile_record
from hhs_nofo_metrics.resolved_scope import (
    ResolvedMeasurementScope,
    calculate_resolved_measurement_scope,
)


@pytest.mark.parametrize(
    "text",
    [
        "An eligible organization as defined by the charter.",
        "Community associations, as defined by the program handbook.",
        "A research partnership as defined by the agreement.",
        "An eligible organization AS DEFINED BY the charter.",
        "An eligible organization as defined expressly by the charter.",
        "An eligible organization as defined by Section 42.",
        "Use the method as defined by the handbook.",
        "The organization, as defined by the charter, applies for support.",
    ],
)
def test_definition_modifier_alone_does_not_make_sentence_passive(text):
    assert released.classify_passive_sentence(text).is_passive
    assert not candidate.classify_passive_sentence(text).is_passive


@pytest.mark.parametrize(
    "text",
    [
        "The award is defined by the agreement.",
        "Eligibility was defined by the board.",
        "The agency defined eligibility and applications were approved.",
        "An organization as defined by the charter is selected annually.",
        "Applications are reviewed for entities as defined by the charter.",
        "An organization as defined by the charter gets selected annually.",
        "An organization as defined by the charter isn't excluded.",
        "An organization as defined by the charter isn’t excluded.",
        "Organizations as defined by the charter have been approved.",
        "Organizations are selected as defined by the charter.",
        "Use the process as approved by the board, as defined by the charter.",
        "Use the process as defined by the charter and as approved by the board.",
        "An organization as defined by the charter. Awards are approved.",
        "Use the amount as specified by the handbook.",
    ],
)
def test_other_passives_survive_definition_modifier_exception(text):
    assert released.classify_passive_sentence(text).is_passive
    assert candidate.classify_passive_sentence(text).is_passive


@pytest.mark.parametrize(
    "text",
    [
        "The applicant is indeed eligible.",
        "Applicants define their goals.",
        "The definition appears in the handbook.",
        "As defined; by Friday applicants respond.",
        "As defined in the handbook, applicants respond.",
        "As defined with additional notes, by Friday applicants respond.",
        "Applicants aren't eligible.",
        "The officers are involved in implementation.",
    ],
)
def test_active_controls_remain_nonpassive(text):
    assert not released.classify_passive_sentence(text).is_passive
    assert not candidate.classify_passive_sentence(text).is_passive


def test_count_once_and_keep_later_passive_match():
    assert (
        candidate.count_passive_sentences(
            (
                "An entity as defined by the charter.",
                "An entity as defined by the charter is selected and is funded.",
                "Use the process as defined by the charter and as approved by the board.",
            )
        )
        == 2
    )


def test_explicit_candidate_changes_only_passive_numerator():
    # Independently enumerated scope: three definition fragments, two genuine
    # passive sentences, one active sentence. All six remain in both scopes.
    sentences = (
        "An eligible organization as defined by the charter.",
        "Community associations, as defined by the program handbook.",
        "A research partnership as defined by the agreement.",
        "The board reviews applications.",
        "Applications are reviewed by the board.",
        "An entity as defined by the charter is selected and is funded.",
    )
    scope = ResolvedMeasurementScope(
        document_status="eligible",
        readability_status="eligible",
        document_content_units=sentences,
        readability_sentences=sentences,
    )
    old = calculate_resolved_measurement_scope(
        scope,
        classify_passive_voice=True,
        passive_method_reference=released.METHOD_REFERENCE,
    )
    new = calculate_resolved_measurement_scope(
        scope,
        classify_passive_voice=True,
        passive_method_reference=candidate.METHOD_REFERENCE,
    )
    assert old.readability_counts.passive_sentence_count == 5
    assert new.readability_counts.passive_sentence_count == 2
    assert (
        old.readability_counts.sentence_count
        == new.readability_counts.sentence_count
        == 6
    )
    assert old.document_word_count == new.document_word_count
    for key, value in old.readability_metrics.items():
        if key != "passive_sentence_percentage":
            assert new.readability_metrics[key] == value
    assert candidate.METHOD_VERSION == "0.5.0-provisional"
    assert released.METHOD_VERSION == "0.4.0-provisional"


def test_candidate_is_not_selected_by_any_packaged_profile():
    for reference in list_profile_references():
        profile, _ = load_profile_record(reference)
        method = profile.methods["passive_classifier"]
        assert f"{method.id}@{method.version}" != candidate.METHOD_REFERENCE
