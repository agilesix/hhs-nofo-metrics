"""Bounded recognition of the repeated NOFO Builder step navigation."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Final

BUILDER_NAVIGATION_METHOD: Final = "builder-step-navigation-pattern@0.1.0"

_LABELS = ("Review", "Get Ready", "Build", "Learn", "Submit", "Award")
_LABEL_RANK = {label.casefold(): rank for rank, label in enumerate(_LABELS, start=1)}
_LABEL_RANK["contacts"] = 7
_TOKEN_RE = re.compile(
    r"(?:(?P<number>[1-6])\.\s*)?"
    r"(?P<label>Review|Get\s+Ready|Build|Learn|Submit|Award|Contacts)",
    re.IGNORECASE,
)
_SEPARATOR_RE = re.compile(r"^[\s|/\u2022\u00b7\u2013\u2014-]*$")


def navigation_tokens(text: str) -> tuple[tuple[int, bool], ...] | None:
    """Parse text containing only Builder navigation labels and separators."""

    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return None
    matches = tuple(_TOKEN_RE.finditer(normalized))
    if not matches:
        return None
    cursor = 0
    tokens: list[tuple[int, bool]] = []
    for match in matches:
        if _SEPARATOR_RE.fullmatch(normalized[cursor : match.start()]) is None:
            return None
        label = re.sub(r"\s+", " ", match.group("label")).casefold()
        tokens.append((_LABEL_RANK[label], match.group("number") is not None))
        cursor = match.end()
    if _SEPARATOR_RE.fullmatch(normalized[cursor:]) is None:
        return None
    return tuple(tokens)


def builder_navigation_item_indexes(
    items: Sequence[tuple[str, int | None]],
) -> frozenset[int]:
    """Find conservative, same-page runs of the Builder navigation sequence."""

    matched: set[int] = set()
    run: list[tuple[int, tuple[tuple[int, bool], ...]]] = []
    run_page: int | None = None

    def finish() -> None:
        if not run:
            return
        tokens = [token for _, values in run for token in values]
        ranks = [rank for rank, _ in tokens]
        numbered = sum(is_numbered for _, is_numbered in tokens)
        qualifies = (
            len(ranks) >= 4
            and ranks == sorted(set(ranks))
            and (numbered >= 2 or (numbered >= 1 and 7 in ranks))
        )
        if qualifies:
            matched.update(index for index, _ in run)

    for index, (text, page) in enumerate(items):
        tokens = navigation_tokens(text)
        if tokens is None or (run and page != run_page):
            finish()
            run = []
            run_page = None
        if tokens is not None:
            if not run:
                run_page = page
            run.append((index, tokens))
        elif run:
            finish()
            run = []
            run_page = None
    finish()
    return frozenset(matched)
