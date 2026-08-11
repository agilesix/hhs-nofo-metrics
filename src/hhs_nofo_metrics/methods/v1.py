"""NOFO Checker's original deterministic readability methods.

These methods intentionally preserve the behavior of NOFO Checker's first
metric implementation so existing results can be reproduced while later
method versions are calibrated against Microsoft Word. In particular, the
tokenizer and syllable estimator are ASCII-oriented and the sentence splitter
uses a small, fixed abbreviation list. Callers should identify this method set
by version rather than treating it as an unversioned definition of English.
"""

from __future__ import annotations

import re
from typing import Final

METHOD_VERSIONS_V1: Final[dict[str, str]] = {
    "word_tokenizer": "nofo-checker-word-tokenizer@1.0.0",
    "sentence_splitter": "nofo-checker-sentence-splitter@1.0.0",
    "character_counter": "nofo-checker-ascii-character-counter@1.0.0",
    "syllable_estimator": "nofo-checker-syllable-estimator@1.0.0",
    "readability_formulas": "flesch-en-us@1.0.0",
}

_WORD_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
_LIST_RE: Final[re.Pattern[str]] = re.compile(r"^\s*(?:[•●▪◻☐☑□*-]|\(?\d{1,3}[.)])\s+")
_ABBREVIATIONS: Final[tuple[str, ...]] = (
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
)


def word_tokens_v1(text: str) -> list[str]:
    """Return NOFO Checker v1 word tokens.

    The method recognizes ASCII-letter words with internal apostrophes or
    hyphens. Numerals and non-ASCII letters are not tokens in this version.
    """

    return _WORD_RE.findall(text)


def split_sentences_v1(text: str) -> list[str]:
    """Return NOFO Checker v1 sentence strings.

    Prose is joined across adjacent nonblank lines and split after ``.``, ``!``
    or ``?`` followed by whitespace. A fixed abbreviation list is protected.
    Recognized list items are sentence candidates of their own. Candidates
    with fewer than two v1 word tokens are excluded.
    """

    sentences: list[str] = []
    prose_lines: list[str] = []

    def flush_prose() -> None:
        if not prose_lines:
            return
        protected = " ".join(prose_lines)
        for index, abbreviation in enumerate(_ABBREVIATIONS):
            protected = protected.replace(abbreviation, f"__ABBR_{index}__")
        parts = re.split(r"(?<=[.!?])(?:[\"')\]]+)?\s+", protected)
        for part in parts:
            for index, abbreviation in enumerate(_ABBREVIATIONS):
                part = part.replace(f"__ABBR_{index}__", abbreviation)
            if len(word_tokens_v1(part)) >= 2:
                sentences.append(part.strip())
        prose_lines.clear()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            flush_prose()
            continue
        if _LIST_RE.match(line):
            flush_prose()
            item = _LIST_RE.sub("", line, count=1).strip()
            if len(word_tokens_v1(item)) >= 2:
                sentences.append(item)
        else:
            prose_lines.append(line)
    flush_prose()
    return sentences


def count_syllables_v1(word: str) -> int:
    """Estimate syllables with NOFO Checker's v1 ASCII vowel heuristic."""

    value = re.sub(r"[^a-z]", "", word.lower())
    if not value:
        return 0
    if len(value) <= 3:
        return 1
    groups = re.findall(r"[aeiouy]+", value)
    count = len(groups)
    if value.endswith("e") and not value.endswith(("le", "ye")) and count > 1:
        count -= 1
    if value.endswith("es") and not value.endswith(("aes", "ees", "oes")) and count > 1:
        count -= 1
    if value.endswith("ed") and not value.endswith(("ted", "ded")) and count > 1:
        count -= 1
    return max(1, count)


def calculate_readability_v1(text: str) -> dict[str, int | float | None]:
    """Calculate raw counts and unrounded NOFO Checker v1 readability values."""

    words = word_tokens_v1(text)
    sentences = split_sentences_v1(text)
    word_count = len(words)
    sentence_count = len(sentences)
    character_count = sum(len(re.sub(r"[^A-Za-z]", "", word)) for word in words)
    syllable_count = sum(count_syllables_v1(word) for word in words)

    words_per_sentence = word_count / sentence_count if sentence_count else None
    characters_per_word = character_count / word_count if word_count else None
    flesch_kincaid_grade = None
    flesch_reading_ease = None
    if word_count and sentence_count:
        flesch_kincaid_grade = (
            0.39 * (word_count / sentence_count)
            + 11.8 * (syllable_count / word_count)
            - 15.59
        )
        flesch_reading_ease = (
            206.835
            - 1.015 * (word_count / sentence_count)
            - 84.6 * (syllable_count / word_count)
        )

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "character_count": character_count,
        "syllable_count": syllable_count,
        "words_per_sentence": words_per_sentence,
        "characters_per_word": characters_per_word,
        "flesch_reading_ease": flesch_reading_ease,
        "flesch_kincaid_grade": flesch_kincaid_grade,
    }
