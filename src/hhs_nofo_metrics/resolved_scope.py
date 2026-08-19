"""Private source-neutral measurement scope and shared metric kernel."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Mapping

from hhs_nofo_metrics.methods import (
    HhsReadabilityScopeCountsDraft,
    calculate_hhs_readability_scope_draft,
    count_passive_sentences,
    tokenize_hhs_readability_draft,
)

RESOLVED_SCOPE_CONTRACT_VERSION: Final = "0.1.0-internal"
SCOPE_STATUSES: Final = frozenset({"eligible", "provisional", "unable"})


def _validate_units(values: tuple[str, ...], label: str) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{label} must be a tuple")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{label} must contain only nonempty text")


@dataclass(frozen=True, slots=True)
class ResolvedMeasurementScope:
    """Private in-memory content after source-specific resolution and policy."""

    document_status: str
    readability_status: str
    document_content_units: tuple[str, ...] = ()
    readability_sentences: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (
            ("document_status", self.document_status),
            ("readability_status", self.readability_status),
        ):
            if value not in SCOPE_STATUSES:
                raise ValueError(f"{name} is unsupported")
        _validate_units(self.document_content_units, "document_content_units")
        _validate_units(self.readability_sentences, "readability_sentences")
        if self.document_status != "eligible" and self.document_content_units:
            raise ValueError("ineligible document scope cannot carry content")
        if self.readability_status != "eligible" and self.readability_sentences:
            raise ValueError("ineligible readability scope cannot carry sentences")


@dataclass(frozen=True, slots=True)
class ResolvedMeasurementCalculation:
    """Text-free counts and values produced by the shared kernel."""

    document_word_count: int | None
    readability_counts: HhsReadabilityScopeCountsDraft | None
    readability_metrics: Mapping[str, int | float | None | str]

    def __post_init__(self) -> None:
        if self.document_word_count is not None and (
            not isinstance(self.document_word_count, int)
            or isinstance(self.document_word_count, bool)
            or self.document_word_count < 0
        ):
            raise ValueError(
                "document_word_count must be a non-negative integer or None"
            )
        object.__setattr__(
            self,
            "readability_metrics",
            MappingProxyType(dict(self.readability_metrics)),
        )
        if (self.readability_counts is None) != (not self.readability_metrics):
            raise ValueError(
                "readability counts and metrics must be present or absent together"
            )


def _token_counts(text_units: tuple[str, ...]) -> tuple[int, int, int]:
    word_count = 0
    character_count = 0
    syllable_count = 0
    for text in text_units:
        tokens = tokenize_hhs_readability_draft(text)
        word_count += len(tokens)
        character_count += sum(token.character_count for token in tokens)
        syllable_count += sum(token.syllable_count for token in tokens)
    return word_count, character_count, syllable_count


def calculate_resolved_measurement_scope(
    scope: ResolvedMeasurementScope,
    *,
    classify_passive_voice: bool = False,
) -> ResolvedMeasurementCalculation:
    """Calculate both HHS scopes after an adapter has resolved their content."""

    document_word_count = None
    if scope.document_status == "eligible":
        document_word_count = _token_counts(scope.document_content_units)[0]

    readability_counts = None
    readability_metrics: Mapping[str, int | float | None | str] = {}
    if scope.readability_status == "eligible":
        words, characters, syllables = _token_counts(scope.readability_sentences)
        readability_counts = HhsReadabilityScopeCountsDraft(
            readability_word_count=words,
            sentence_count=len(scope.readability_sentences),
            character_count=characters,
            syllable_count=syllables,
            passive_sentence_count=(
                count_passive_sentences(scope.readability_sentences)
                if classify_passive_voice
                else None
            ),
        )
        readability_metrics = calculate_hhs_readability_scope_draft(readability_counts)

    return ResolvedMeasurementCalculation(
        document_word_count=document_word_count,
        readability_counts=readability_counts,
        readability_metrics=readability_metrics,
    )


__all__ = [
    "RESOLVED_SCOPE_CONTRACT_VERSION",
    "ResolvedMeasurementCalculation",
    "ResolvedMeasurementScope",
    "calculate_resolved_measurement_scope",
]
