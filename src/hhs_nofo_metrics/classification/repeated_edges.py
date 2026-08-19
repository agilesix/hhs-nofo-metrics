"""Versioned detection of repeated page-edge text.

Detection labels candidates; it never deletes extracted content. Profiles
decide whether a labeled segment contributes to a metric.
"""

from __future__ import annotations

import math
import re
from collections import Counter

METHOD_ID = "hhs-repeated-edge"
METHOD_VERSION = "1.0.0"


def normalize_edge_text(text: str) -> str:
    value = re.sub(r"\s+", " ", text).strip().casefold()
    return re.sub(r"\d+", "#", value)


def find_repeated_edge_patterns(
    page_lines: list[list[str]],
    *,
    edge_line_count: int = 3,
    minimum_page_fraction: float = 0.30,
    minimum_pages: int = 3,
) -> dict[str, int]:
    """Return normalized edge lines repeated across enough pages."""
    if not page_lines:
        return {}
    threshold = max(
        minimum_pages,
        math.ceil(len(page_lines) * minimum_page_fraction),
    )
    counts: Counter[str] = Counter()
    for lines in page_lines:
        candidates = lines[:edge_line_count] + lines[-edge_line_count:]
        for line in set(candidates):
            normalized = normalize_edge_text(line)
            if 3 <= len(normalized) <= 180:
                counts[normalized] += 1
    return {pattern: count for pattern, count in counts.items() if count >= threshold}


def is_page_edge(index: int, line_count: int, edge_line_count: int = 3) -> bool:
    return index < edge_line_count or index >= max(0, line_count - edge_line_count)
