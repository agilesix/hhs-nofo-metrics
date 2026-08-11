"""Versioned deterministic passive-sentence classification.

The method deliberately recognizes bounded English passive constructions rather
than claiming to reproduce Microsoft Word's private grammar checker. A sentence
is passive when it contains a bounded finite passive. The narrow phrase
``as + participle + by`` is also recognized, while broader reduced passives and
bounded adjectival-state patterns are excluded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

METHOD_ID: Final = "hhs-nofo-passive-sentence-rule"
METHOD_VERSION: Final = "0.3.0-provisional"
METHOD_REFERENCE: Final = f"{METHOD_ID}@{METHOD_VERSION}"

_WORD_RE: Final = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
_PASSIVE_AUXILIARIES: Final = frozenset(
    {
        "am",
        "are",
        "be",
        "been",
        "being",
        "get",
        "gets",
        "getting",
        "got",
        "gotten",
        "is",
        "was",
        "were",
    }
)
_INTERVENING_WORDS: Final = frozenset(
    {
        "also",
        "already",
        "always",
        "being",
        "been",
        "currently",
        "directly",
        "duly",
        "ever",
        "expressly",
        "fully",
        "generally",
        "in",
        "indirectly",
        "never",
        "no",
        "not",
        "now",
        "only",
        "otherwise",
        "partially",
        "properly",
        "regularly",
        "separately",
        "specifically",
        "still",
        "then",
        "typically",
        "usually",
        "well",
        "yet",
    }
)
_IRREGULAR_PARTICIPLES: Final = frozenset(
    {
        "arisen",
        "awoken",
        "begun",
        "bent",
        "bound",
        "broken",
        "brought",
        "built",
        "bought",
        "caught",
        "chosen",
        "come",
        "cost",
        "cut",
        "dealt",
        "done",
        "drawn",
        "driven",
        "eaten",
        "fallen",
        "fed",
        "felt",
        "fled",
        "flown",
        "forbidden",
        "forgotten",
        "forgiven",
        "found",
        "frozen",
        "given",
        "gone",
        "grown",
        "had",
        "heard",
        "held",
        "hidden",
        "hit",
        "hurt",
        "kept",
        "known",
        "laid",
        "led",
        "left",
        "lent",
        "let",
        "lost",
        "made",
        "meant",
        "met",
        "paid",
        "put",
        "read",
        "ridden",
        "risen",
        "run",
        "said",
        "seen",
        "sent",
        "set",
        "shown",
        "shut",
        "sold",
        "sought",
        "spent",
        "split",
        "spoken",
        "stolen",
        "stuck",
        "sung",
        "sunk",
        "sworn",
        "swept",
        "swum",
        "taken",
        "taught",
        "told",
        "thought",
        "thrown",
        "understood",
        "woken",
        "won",
        "worn",
        "written",
    }
)
_CLAUSE_BOUNDARY_RE: Final = re.compile(r"[.;:!?]")
_GET_RESULTATIVE_EXCLUSIONS: Final = frozenset({"started"})
_UNAMBIGUOUS_ADJECTIVES: Final = frozenset(
    {"underinsured", "uninsured", "unrestricted"}
)
_ADJECTIVAL_COMPLEMENTS: Final = {
    "associated": frozenset({"with"}),
    "interested": frozenset({"in"}),
    "involved": frozenset({"in", "with"}),
    "positioned": frozenset({"to"}),
    "prepared": frozenset({"to"}),
}


@dataclass(frozen=True, slots=True)
class PassiveSentenceClassification:
    """Text-free classification evidence for one sentence."""

    is_passive: bool
    rule: str


def _is_likely_participle(word: str) -> bool:
    return word in _IRREGULAR_PARTICIPLES or (
        len(word) >= 4 and (word.endswith("ed") or word.endswith("ied"))
    )


def _is_bounded_adjectival_usage(
    words: tuple[str, ...], auxiliary_index: int, candidate_index: int
) -> bool:
    """Reject explicit state/adjective patterns without general POS guessing."""

    candidate = words[candidate_index]
    if candidate in _UNAMBIGUOUS_ADJECTIVES:
        return True
    following = words[candidate_index + 1] if candidate_index + 1 < len(words) else None
    if following in _ADJECTIVAL_COMPLEMENTS.get(candidate, frozenset()):
        return True
    # In existential clauses the participle modifies the following noun; it is
    # not the predicate of a passive clause (for example, "there are proposed
    # subawards" or "there is no set limit").
    return (
        "there" in words[max(0, auxiliary_index - 2) : auxiliary_index]
        and following is not None
        and following != "by"
    )


def classify_passive_sentence(sentence: str) -> PassiveSentenceClassification:
    """Classify one already-segmented English sentence deterministically."""

    matches = tuple(_WORD_RE.finditer(sentence))
    words = tuple(match.group(0).lower().replace("’", "'") for match in matches)
    for auxiliary_index, auxiliary in enumerate(words):
        if auxiliary not in _PASSIVE_AUXILIARIES:
            continue
        for candidate_index in range(
            auxiliary_index + 1, min(len(words), auxiliary_index + 6)
        ):
            between = sentence[
                matches[candidate_index - 1].end() : matches[candidate_index].start()
            ]
            if _CLAUSE_BOUNDARY_RE.search(between):
                break
            candidate = words[candidate_index]
            if _is_likely_participle(candidate):
                if _is_bounded_adjectival_usage(
                    words, auxiliary_index, candidate_index
                ):
                    break
                if (
                    auxiliary in {"get", "gets", "getting", "got", "gotten"}
                    and candidate in _GET_RESULTATIVE_EXCLUSIONS
                ):
                    break
                return PassiveSentenceClassification(
                    is_passive=True,
                    rule=(
                        "be_auxiliary_plus_participle"
                        if auxiliary not in {"get", "gets", "getting", "got", "gotten"}
                        else "get_auxiliary_plus_participle"
                    ),
                )
            if candidate not in _INTERVENING_WORDS and not candidate.endswith("ly"):
                break

    for candidate_index, candidate in enumerate(words[1:], start=1):
        if words[candidate_index - 1] != "as" or not _is_likely_participle(candidate):
            continue
        for by_index in range(
            candidate_index + 1, min(len(words), candidate_index + 5)
        ):
            between = sentence[matches[by_index - 1].end() : matches[by_index].start()]
            if _CLAUSE_BOUNDARY_RE.search(between):
                break
            following = words[by_index]
            if following == "by":
                return PassiveSentenceClassification(
                    is_passive=True,
                    rule="as_participle_plus_by",
                )
            if following not in _INTERVENING_WORDS and not following.endswith("ly"):
                break

    return PassiveSentenceClassification(is_passive=False, rule="no_bounded_passive")


def count_passive_sentences(sentences: tuple[str, ...]) -> int:
    """Count passive sentences in the supplied resolved sentence scope."""

    return sum(classify_passive_sentence(sentence).is_passive for sentence in sentences)


__all__ = [
    "METHOD_ID",
    "METHOD_REFERENCE",
    "METHOD_VERSION",
    "PassiveSentenceClassification",
    "classify_passive_sentence",
    "count_passive_sentences",
]
