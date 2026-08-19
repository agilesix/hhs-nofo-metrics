"""Non-operative arithmetic contract for a proposed HHS readability method.

This module deliberately starts after selection, tokenization, sentence
inventory construction, and syllable classification. It makes the denominator
relationships testable without activating an unapproved policy in the metric
engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

HHS_READABILITY_ARITHMETIC_DRAFT_ID: Final = "hhs-nofo-readability-arithmetic"
HHS_READABILITY_ARITHMETIC_DRAFT_VERSION: Final = "0.1.0-draft"
HHS_READABILITY_ARITHMETIC_DRAFT_REFERENCE: Final = (
    f"{HHS_READABILITY_ARITHMETIC_DRAFT_ID}@{HHS_READABILITY_ARITHMETIC_DRAFT_VERSION}"
)


@dataclass(frozen=True, slots=True)
class HhsReadabilityScopeCountsDraft:
    """Upstream counts for the narrower readability-sentence scope."""

    readability_word_count: int
    sentence_count: int
    character_count: int
    syllable_count: int
    passive_sentence_count: int | None = None

    def __post_init__(self) -> None:
        required = {
            "readability_word_count": self.readability_word_count,
            "sentence_count": self.sentence_count,
            "character_count": self.character_count,
            "syllable_count": self.syllable_count,
        }
        for name, value in required.items():
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.passive_sentence_count is not None and (
            not isinstance(self.passive_sentence_count, int)
            or isinstance(self.passive_sentence_count, bool)
            or self.passive_sentence_count < 0
        ):
            raise ValueError(
                "passive_sentence_count must be a non-negative integer or None"
            )
        if self.sentence_count and not self.readability_word_count:
            raise ValueError(
                "sentence_count requires a non-zero readability_word_count"
            )
        if not self.readability_word_count and (
            self.character_count or self.syllable_count
        ):
            raise ValueError(
                "character_count and syllable_count require readability words"
            )
        if (
            self.passive_sentence_count is not None
            and self.passive_sentence_count > self.sentence_count
        ):
            raise ValueError("passive_sentence_count must not exceed sentence_count")


@dataclass(frozen=True, slots=True)
class HhsReadabilityCountsDraft:
    """Approved document and sentence-scope counts for draft arithmetic.

    ``document_word_count`` is the standalone Word Count metric.
    ``readability_word_count`` contains only words in included sentence
    inventory items and is the numerator for sentence length and Flesch
    calculations.
    """

    document_word_count: int
    readability_word_count: int
    sentence_count: int
    character_count: int
    syllable_count: int
    passive_sentence_count: int | None = None

    def __post_init__(self) -> None:
        HhsReadabilityScopeCountsDraft(
            readability_word_count=self.readability_word_count,
            sentence_count=self.sentence_count,
            character_count=self.character_count,
            syllable_count=self.syllable_count,
            passive_sentence_count=self.passive_sentence_count,
        )
        if (
            not isinstance(self.document_word_count, int)
            or isinstance(self.document_word_count, bool)
            or self.document_word_count < 0
        ):
            raise ValueError("document_word_count must be a non-negative integer")
        if self.readability_word_count > self.document_word_count:
            raise ValueError(
                "readability_word_count must not exceed document_word_count"
            )


def calculate_hhs_readability_scope_draft(
    counts: HhsReadabilityScopeCountsDraft,
) -> dict[str, int | float | None | str]:
    """Calculate unrounded metrics for the readability sentence scope."""

    words_per_sentence = (
        counts.readability_word_count / counts.sentence_count
        if counts.sentence_count
        else None
    )
    characters_per_word = (
        counts.character_count / counts.readability_word_count
        if counts.readability_word_count
        else None
    )
    syllables_per_word = (
        counts.syllable_count / counts.readability_word_count
        if counts.readability_word_count
        else None
    )
    flesch_reading_ease = None
    flesch_kincaid_grade_level = None
    if words_per_sentence is not None and syllables_per_word is not None:
        flesch_reading_ease = (
            206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
        )
        flesch_kincaid_grade_level = (
            0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
        )
    passive_sentence_percentage = (
        100 * counts.passive_sentence_count / counts.sentence_count
        if counts.passive_sentence_count is not None and counts.sentence_count
        else None
    )
    return {
        "method": HHS_READABILITY_ARITHMETIC_DRAFT_REFERENCE,
        "readability_word_count": counts.readability_word_count,
        "sentence_count": counts.sentence_count,
        "syllable_count": counts.syllable_count,
        "character_count": counts.character_count,
        "words_per_sentence": words_per_sentence,
        "characters_per_word": characters_per_word,
        "flesch_reading_ease": flesch_reading_ease,
        "flesch_kincaid_grade_level": flesch_kincaid_grade_level,
        "passive_sentence_percentage": passive_sentence_percentage,
    }


def calculate_hhs_readability_draft(
    counts: HhsReadabilityCountsDraft,
) -> dict[str, int | float | None | str]:
    """Calculate unrounded draft metrics from explicit upstream counts.

    The formulas are the published English Flesch formulas. ``None`` means the
    required denominator or approved passive classification is unavailable.
    No display rounding, score bands, or enforcement thresholds are applied.
    """

    scope = calculate_hhs_readability_scope_draft(counts)
    return {
        "method": scope["method"],
        "word_count": counts.document_word_count,
        **{key: value for key, value in scope.items() if key != "method"},
    }
