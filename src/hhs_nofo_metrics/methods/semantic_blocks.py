"""Sentence inventory for semantic source blocks.

Block boundaries are authoritative. Only terminally punctuated candidates are
readability sentences; a trailing fragment stays excluded instead of being
joined to a neighboring list item, table cell, or paragraph.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

METHOD_ID: Final = "hhs-semantic-block-sentence-segmentation"
METHOD_VERSION: Final = "0.1.0"
METHOD_REFERENCE: Final = f"{METHOD_ID}@{METHOD_VERSION}"

_SENTINEL = "\ue000"
_ABBREVIATIONS = (
    "e.g.",
    "i.e.",
    "etc.",
    "U.S.",
    "No.",
    "Mr.",
    "Ms.",
    "Dr.",
    "Inc.",
    "vs.",
    "a.m.",
    "p.m.",
)
_TERMINAL_RE = re.compile(r"[.!?]+(?:[\"'’”)]*)?(?=\s|$)")
_TOKEN_WITH_DOTS_RE = re.compile(
    r"(?:https?://|www\.)\S+|\b[\w.+-]+@[\w.-]+\.\w+\b|\b(?:[A-Za-z]\.){2,}"
)


@dataclass(frozen=True, slots=True)
class SemanticSentenceSplit:
    sentences: tuple[str, ...]
    excluded_fragments: tuple[str, ...]


def _protect_dots(text: str) -> str:
    protected = re.sub(r"(?<=\d)\.(?=\d)", _SENTINEL, text)
    for abbreviation in _ABBREVIATIONS:
        protected = re.sub(
            rf"(?<!\w){re.escape(abbreviation)}(?!\w)",
            abbreviation.replace(".", _SENTINEL),
            protected,
            flags=re.IGNORECASE,
        )
    protected = _TOKEN_WITH_DOTS_RE.sub(
        lambda match: match.group(0).replace(".", _SENTINEL), protected
    )
    protected = re.sub(rf"{_SENTINEL}(?=(?:[\"'’”)]*)$)", ".", protected)
    return protected


def split_semantic_block_sentences(text: str) -> SemanticSentenceSplit:
    """Split one semantic block without crossing its structural boundary."""

    if not isinstance(text, str):
        raise TypeError("semantic sentence input must be text")
    protected = _protect_dots(text.strip())
    sentences: list[str] = []
    cursor = 0
    for match in _TERMINAL_RE.finditer(protected):
        candidate = protected[cursor : match.end()].strip().replace(_SENTINEL, ".")
        if candidate:
            sentences.append(candidate)
        cursor = match.end()
    remainder = protected[cursor:].strip().replace(_SENTINEL, ".")
    return SemanticSentenceSplit(
        sentences=tuple(sentences),
        excluded_fragments=(remainder,) if remainder else (),
    )


__all__ = [
    "METHOD_ID",
    "METHOD_REFERENCE",
    "METHOD_VERSION",
    "SemanticSentenceSplit",
    "split_semantic_block_sentences",
]
