"""Invented controls for the October 29 manual comparison follow-up."""

import pytest

from hhs_nofo_metrics import SourceBundle, analyze

PROFILES = ("hhs-nofo-fy27-html@0.5.0", "hhs-nofo-fy27-html@0.6.0")
PAIRS = (
    ("Workshop seating is not guaranteed.", "We do not guarantee workshop seating."),
    (
        "Printed badges may not be required.",
        "Organizers may not require printed badges.",
    ),
    ("Is submitted after the workshop.", "You submit after the workshop."),
)


def measure(texts):
    return SourceBundle.from_html("".join(f"<p>{text}</p>" for text in texts).encode())


@pytest.mark.parametrize("profile", PROFILES)
@pytest.mark.parametrize("passive,active", PAIRS)
def test_active_rewrite_changes_numerator_without_removing_sentence(
    profile, passive, active
):
    # Independently specified: two punctuated blocks, one passive then none.
    before = analyze(
        measure((passive, "Participants read the schedule.")), profile=profile
    )
    after = analyze(
        measure((active, "Participants read the schedule.")), profile=profile
    )
    for result, expected_count, expected_percent in ((before, 1, 50), (after, 0, 0)):
        metric = result.metrics["passive_sentence_percentage"]
        assert metric.components["sentence_count"] == 2
        assert metric.components["passive_sentence_count"] == expected_count
        assert metric.value == expected_percent
        assert result.metrics["words_per_sentence"].components["sentence_count"] == 2


@pytest.mark.parametrize("profile", PROFILES)
def test_added_active_sentences_change_denominator_not_passive_count(profile):
    texts = ("The room is cleaned by volunteers.", "Visitors arrive early.")
    before = analyze(measure(texts), profile=profile)
    after = analyze(
        measure((*texts, "Staff greet visitors.", "Guests read the schedule.")),
        profile=profile,
    )
    for result, sentences, percent in ((before, 2, 50), (after, 4, 25)):
        metric = result.metrics["passive_sentence_percentage"]
        assert metric.components["passive_sentence_count"] == 1
        assert metric.components["sentence_count"] == sentences
        assert metric.value == percent
