from __future__ import annotations

import pytest

from hhs_nofo_metrics.methods import (
    HHS_READABILITY_ARITHMETIC_DRAFT_REFERENCE,
    METHOD_VERSIONS_V1,
    HhsReadabilityCountsDraft,
    HhsReadabilityScopeCountsDraft,
    calculate_hhs_readability_draft,
    calculate_hhs_readability_scope_draft,
    classify_passive_sentence,
    count_passive_sentences,
    count_syllables_v1,
    split_sentences_v1,
    word_tokens_v1,
)


def test_hhs_arithmetic_separates_document_and_readability_scopes() -> None:
    result = calculate_hhs_readability_draft(
        HhsReadabilityCountsDraft(
            document_word_count=120,
            readability_word_count=100,
            sentence_count=5,
            character_count=500,
            syllable_count=150,
            passive_sentence_count=2,
        )
    )

    assert result["method"] == HHS_READABILITY_ARITHMETIC_DRAFT_REFERENCE
    assert result["word_count"] == 120
    assert result["readability_word_count"] == 100
    assert result["words_per_sentence"] == 20
    assert result["characters_per_word"] == 5
    assert result["passive_sentence_percentage"] == 40


def test_hhs_arithmetic_keeps_unavailable_denominators_explicit() -> None:
    result = calculate_hhs_readability_draft(
        HhsReadabilityCountsDraft(
            document_word_count=12,
            readability_word_count=0,
            sentence_count=0,
            character_count=0,
            syllable_count=0,
        )
    )

    assert result["word_count"] == 12
    assert result["words_per_sentence"] is None
    assert result["characters_per_word"] is None
    assert result["flesch_reading_ease"] is None
    assert result["flesch_kincaid_grade_level"] is None
    assert result["passive_sentence_percentage"] is None


def test_hhs_scope_arithmetic_does_not_claim_document_word_count() -> None:
    result = calculate_hhs_readability_scope_draft(
        HhsReadabilityScopeCountsDraft(
            readability_word_count=20,
            sentence_count=2,
            character_count=100,
            syllable_count=30,
        )
    )

    assert "word_count" not in result
    assert result["words_per_sentence"] == 10
    assert result["characters_per_word"] == 5


@pytest.mark.parametrize(
    "values",
    [
        (-1, 0, 0, 0, 0, None),
        (10, 11, 1, 40, 14, None),
        (10, 0, 1, 0, 0, None),
        (10, 0, 0, 1, 0, None),
        (10, 10, 1, 40, 14, 2),
    ],
)
def test_hhs_count_contract_rejects_incoherent_counts(
    values: tuple[int, int, int, int, int, int | None],
) -> None:
    with pytest.raises(ValueError):
        HhsReadabilityCountsDraft(*values)


def test_v1_method_set_has_independently_versioned_components() -> None:
    assert METHOD_VERSIONS_V1 == {
        "word_tokenizer": "nofo-checker-word-tokenizer@1.0.0",
        "sentence_splitter": "nofo-checker-sentence-splitter@1.0.0",
        "character_counter": "nofo-checker-ascii-character-counter@1.0.0",
        "syllable_estimator": "nofo-checker-syllable-estimator@1.0.0",
        "readability_formulas": "flesch-en-us@1.0.0",
    }


@pytest.mark.parametrize(
    "sentence",
    [
        "Applications are reviewed by independent experts.",
        "The award will be made in September.",
        "The plan is being evaluated.",
        "Costs have been approved.",
        "Your application must not be submitted after the deadline.",
        "Applicants may get selected for an interview.",
        "Caregivers are regularly identified by providers.",
        "The partnerships are well described.",
        "Use the method as defined by statute.",
        "See information on getting registered.",
    ],
)
def test_passive_sentence_rule_recognizes_bounded_passives(sentence: str) -> None:
    result = classify_passive_sentence(sentence)

    assert result.is_passive is True
    assert result.rule in {
        "be_auxiliary_plus_participle",
        "get_auxiliary_plus_participle",
        "as_participle_plus_by",
    }


@pytest.mark.parametrize(
    "sentence",
    [
        "Applicants submit forms.",
        "Applicants have submitted forms.",
        "Awards are available.",
        "The costs are reasonable and consistent.",
        "The applicant is being responsible.",
        "Activities approved by HHS may begin.",
        "The issues addressed by the program require coordination.",
        "Go to SAM.gov Entity Registration and select Get Started.",
        "You can get started before registrations are complete.",
        "People who are uninsured or underinsured need assistance.",
        "Show that you are prepared to track performance data.",
        "They are well positioned to help applicants.",
        "The officers are involved in implementation.",
        "These conditions are associated with poor outcomes.",
        "We are interested in clear narratives.",
        "Eligibility is unrestricted.",
        "There are proposed subawards in the budget.",
        "There is no set limit on the incentive.",
        "Reviewers will score applications.",
        "We have approved the plan.",
    ],
)
def test_passive_sentence_rule_rejects_active_and_stative_sentences(
    sentence: str,
) -> None:
    assert classify_passive_sentence(sentence).is_passive is False


def test_passive_sentence_count_uses_the_supplied_sentence_denominator() -> None:
    sentences = (
        "Applications are reviewed by independent experts.",
        "Applicants submit forms.",
        "The award will be made in September.",
        "Awards are available.",
    )

    assert count_passive_sentences(sentences) == 2


def test_v1_preserves_frozen_token_and_sentence_behavior() -> None:
    text = "1. Apply now\n\u2022 Wait here\nA prose sentence follows."

    assert word_tokens_v1(
        "HHS-2026-ACF funds Jos\u00e9's applicant\u2019s programs."
    ) == [
        "HHS",
        "ACF",
        "funds",
        "Jos",
        "s",
        "applicant\u2019s",
        "programs",
    ]
    assert split_sentences_v1(text) == [
        "Apply now",
        "Wait here",
        "A prose sentence follows.",
    ]


@pytest.mark.parametrize(
    ("word", "expected"),
    [("", 0), ("HHS", 1), ("make", 1), ("table", 2), ("funded", 2)],
)
def test_v1_syllable_estimator_regression(word: str, expected: int) -> None:
    assert count_syllables_v1(word) == expected
