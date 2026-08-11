"""Pure, versioned token candidates shared by measurement methods."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Final

from .v1 import count_syllables_v1, word_tokens_v1

READABILITY_CHARACTER_CANDIDATE_REFERENCE: Final = (
    "word-readability-character-token-candidate@0.1.0"
)
SYLLABLE_CANDIDATE_METHOD_ID: Final = "word-syllable-candidate"
SYLLABLE_CANDIDATE_METHOD_VERSION: Final = "0.1.0"
SYLLABLE_CANDIDATE_METHOD_REFERENCE: Final = (
    f"{SYLLABLE_CANDIDATE_METHOD_ID}@{SYLLABLE_CANDIDATE_METHOD_VERSION}"
)

_IGNORED_MARKERS: Final = {"•", "\uf0b7", "◦", "◻", "☐", "☑", "□"}
_KNOWN_ABBREVIATIONS: Final = {
    "Dr.",
    "Mr.",
    "Mrs.",
    "Ms.",
    "U.S.",
    "U.S.C.",
    "e.g.",
    "i.e.",
    "p.m.",
    "a.m.",
}
_DELIMITER_RE: Final = re.compile(r"://|[/\\]|[–—]")
_NUMERIC_OUTLINE_RE: Final = re.compile(r"\d+[.)]")
_DOTTED_NUMERIC_TERMINAL_RE: Final = re.compile(r"\d+(?:\.\d+)+\.")
_NUMERIC_RE: Final = re.compile(
    r"(?P<currency>\$)?(?P<number>\d[\d,]*(?:\.\d+)?)(?P<percent>%)?"
)
_UNICODE_WORD_RE: Final = re.compile(
    r"[^\W\d_]+(?:['’\-][^\W\d_]+)*",
    re.UNICODE,
)
_SYLLABLE_EXCEPTIONS: Final[dict[str, int]] = {
    "aaliyah": 3,
    "schedule": 2,
    "uei": 2,
    "résumé": 3,
}


def readability_character_tokens_candidate_v0_1_0(text: str) -> list[str]:
    """Return provisional tokens for Word's Characters per Word display."""

    chunks = re.findall(r"\S+", text)
    tokens: list[str] = []
    for index, chunk in enumerate(chunks):
        if chunk in _IGNORED_MARKERS:
            continue
        next_chunk = chunks[index + 1] if index + 1 < len(chunks) else None
        parts = _DELIMITER_RE.split(chunk)
        for part_index, part in enumerate(parts):
            if not part:
                continue
            value = part.lstrip('"“‘([{')
            is_last_part = part_index == len(parts) - 1
            terminal_context = next_chunk is None or (
                next_chunk
                and next_chunk[0].isupper()
                and chunk not in _KNOWN_ABBREVIATIONS
            )
            preserve_numeric_terminal = bool(
                _NUMERIC_OUTLINE_RE.fullmatch(value)
                or _DOTTED_NUMERIC_TERMINAL_RE.fullmatch(value)
            )
            if (
                is_last_part
                and terminal_context
                and chunk not in _KNOWN_ABBREVIATIONS
                and not preserve_numeric_terminal
            ):
                core = value.rstrip('"”’)]}')
                closing = value[len(core) :]
                if core.endswith((".", "!", "?")):
                    value = core[:-1] + closing
                elif value.endswith((".", "!", "?")):
                    value = value[:-1]
            value = value.rstrip('"”’)]},;:')
            if value:
                tokens.append(value)
    return tokens


def _ascii_letters(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character) and character.isascii()
    )


def _ordinary_word_syllables(value: str) -> tuple[int, str]:
    lowered = value.casefold()
    if lowered in _SYLLABLE_EXCEPTIONS:
        return _SYLLABLE_EXCEPTIONS[lowered], "exception"
    return count_syllables_v1(_ascii_letters(value)), "unicode_normalized_v1"


def _numeric_syllables(match: re.Match[str]) -> tuple[int, str]:
    number = match.group("number")
    digits = sum(character.isdigit() for character in number)
    decimal_points = number.count(".")
    currency = match.group("currency") is not None
    count = digits + decimal_points + (1 if currency and digits > 1 else 0)
    return max(1, count), "numeric_pattern"


def syllable_candidate_breakdown_v0_1_0(text: str) -> dict[str, Any]:
    """Return provisional syllable totals with token-level reasons."""

    items: list[dict[str, Any]] = []
    for raw_chunk in re.findall(r"\S+", text):
        if raw_chunk in _IGNORED_MARKERS:
            continue
        chunk = raw_chunk.strip('"“”‘’()[]{}.,;:!?')
        if not chunk:
            continue
        if chunk.startswith(("http://", "https://")) or "@" in chunk:
            parts = word_tokens_v1(chunk)
            count = sum(count_syllables_v1(part) for part in parts)
            word_units = (
                sum(bool(part) for part in re.split(r"://|/", chunk))
                if chunk.startswith(("http://", "https://"))
                else 1
            )
            items.append(
                {
                    "token": chunk,
                    "syllables": count,
                    "word_units": word_units,
                    "reason": "electronic_v1_components",
                    "components": parts,
                }
            )
            continue
        numeric = _NUMERIC_RE.fullmatch(chunk)
        if numeric:
            count, reason = _numeric_syllables(numeric)
            items.append(
                {
                    "token": chunk,
                    "syllables": count,
                    "word_units": 1,
                    "reason": reason,
                }
            )
            continue
        if any(character.isdigit() for character in chunk) and any(
            character.isalpha() for character in chunk
        ):
            items.append(
                {
                    "token": chunk,
                    "syllables": 1,
                    "word_units": 1,
                    "reason": "mixed_identifier",
                }
            )
            continue
        for word in _UNICODE_WORD_RE.findall(chunk):
            count, reason = _ordinary_word_syllables(word)
            items.append(
                {
                    "token": word,
                    "syllables": count,
                    "word_units": 1,
                    "reason": reason,
                }
            )
    return {
        "method": SYLLABLE_CANDIDATE_METHOD_REFERENCE,
        "syllable_count": sum(item["syllables"] for item in items),
        "token_count": sum(item["word_units"] for item in items),
        "items": items,
    }


def syllable_candidate_count_v0_1_0(text: str) -> int:
    """Return the provisional total syllable count."""

    return int(syllable_candidate_breakdown_v0_1_0(text)["syllable_count"])
