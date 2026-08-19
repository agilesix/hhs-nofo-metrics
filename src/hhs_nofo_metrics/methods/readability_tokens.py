"""Shared word-unit stream for provisional HHS readability metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .token_candidates import (
    READABILITY_CHARACTER_CANDIDATE_REFERENCE,
    SYLLABLE_CANDIDATE_METHOD_REFERENCE,
    readability_character_tokens_candidate_v0_1_0,
    syllable_candidate_breakdown_v0_1_0,
)

HHS_READABILITY_TOKEN_DRAFT_ID: Final = "hhs-nofo-readability-token-stream"
HHS_READABILITY_TOKEN_DRAFT_VERSION: Final = "0.1.0-internal"
HHS_READABILITY_TOKEN_DRAFT_REFERENCE: Final = (
    f"{HHS_READABILITY_TOKEN_DRAFT_ID}@{HHS_READABILITY_TOKEN_DRAFT_VERSION}"
)
HHS_READABILITY_TOKEN_DRAFT_COMPONENTS: Final = (
    READABILITY_CHARACTER_CANDIDATE_REFERENCE,
    SYLLABLE_CANDIDATE_METHOD_REFERENCE,
)


@dataclass(frozen=True, slots=True)
class HhsReadabilityTokenDraft:
    """One shared readability word unit and its derived attributes."""

    surface: str
    character_count: int
    syllable_count: int

    def __post_init__(self) -> None:
        if not self.surface or self.surface.isspace():
            raise ValueError("readability token surface must contain text")
        if self.character_count != len(self.surface):
            raise ValueError("readability token character count must match its surface")
        if (
            not isinstance(self.syllable_count, int)
            or isinstance(self.syllable_count, bool)
            or self.syllable_count < 0
        ):
            raise ValueError("readability token syllable count must be non-negative")


def tokenize_hhs_readability_draft(
    text: str,
) -> tuple[HhsReadabilityTokenDraft, ...]:
    """Create one provisional word-unit stream for all readability metrics."""

    if not isinstance(text, str):
        raise TypeError("readability token input must be text")
    surfaces = readability_character_tokens_candidate_v0_1_0(text)
    return tuple(
        HhsReadabilityTokenDraft(
            surface=surface,
            character_count=len(surface),
            syllable_count=int(
                syllable_candidate_breakdown_v0_1_0(surface)["syllable_count"]
            ),
        )
        for surface in surfaces
    )


__all__ = [
    "HHS_READABILITY_TOKEN_DRAFT_COMPONENTS",
    "HHS_READABILITY_TOKEN_DRAFT_ID",
    "HHS_READABILITY_TOKEN_DRAFT_REFERENCE",
    "HHS_READABILITY_TOKEN_DRAFT_VERSION",
    "HhsReadabilityTokenDraft",
    "tokenize_hhs_readability_draft",
]
