"""Measure converted Word HTML using verified, conversion-only boundaries."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from typing import Mapping

from hhs_nofo_metrics.errors import AdapterContractError
from hhs_nofo_metrics.sources import MaterializedSourceBundle

from .contracts import AdapterResult, JsonValue
from .html import HtmlAdapterPlugin, _DomParser, _inline_text, _Node, _semantic_blocks

_MARKER = re.compile(r"scope_[0-9a-f]{16}_[0-9]+")
_ROLES = {"cover", "cover_position", "table_of_contents", "instruction", "metadata"}
_MARKABLE = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li"}


def _mapped_roles(root: _Node, markers: Mapping[str, str]) -> dict[int, str]:
    """Apply a role only when both markers bound a single whole HTML block."""
    occurrences: Counter[str] = Counter()
    candidates: list[tuple[_Node, str]] = []
    pending = [root]
    while pending:
        node = pending.pop()
        children = [child for child in node.children if isinstance(child, _Node)]
        pending.extend(children)
        if node.tag == "a" and node.attrs.get("id") in markers:
            occurrences[node.attrs["id"]] += 1
        if node.tag not in _MARKABLE:
            continue
        substantive = [
            child
            for child in node.children
            if (isinstance(child, _Node) or child.strip())
        ]
        if len(substantive) < 2:
            continue
        first, last = substantive[0], substantive[-1]
        if not (
            isinstance(first, _Node)
            and isinstance(last, _Node)
            and first.tag == last.tag == "a"
            and not _inline_text(first)
            and not _inline_text(last)
        ):
            continue
        start = first.attrs.get("id", "")
        end = last.attrs.get("id", "")
        if start.endswith("_s") and start[:-2] + "_e" == end and start in markers:
            candidates.append((node, start))
    return {
        id(node): markers[start]
        for node, start in candidates
        if occurrences[start] == occurrences[start[:-2] + "_e"] == 1
    }


class WordHtmlAdapterPlugin(HtmlAdapterPlugin):
    descriptor = replace(
        HtmlAdapterPlugin.descriptor,
        id="hhs-word-derived-html-adapter",
        version="0.1.0",
    )

    def extract(
        self, source: MaterializedSourceBundle, *, config: Mapping[str, JsonValue]
    ) -> AdapterResult:
        raw_markers = config.get("word_boundaries")
        if set(config) != {"word_boundaries"} or not isinstance(raw_markers, dict):
            raise AdapterContractError(
                "Word HTML requires conversion boundary evidence"
            )
        markers: dict[str, str] = {}
        for prefix, role in raw_markers.items():
            if (
                not _MARKER.fullmatch(prefix)
                or not isinstance(role, str)
                or role not in _ROLES
            ):
                raise AdapterContractError("Invalid Word conversion boundary evidence")
            markers[prefix + "_s"] = markers[prefix + "_e"] = role
        baseline = super().extract(source, config={})
        parser = _DomParser()
        parser.feed(source.primary.path.read_text(encoding="utf-8"))
        parser.close()
        blocks = _semantic_blocks(parser.root, _mapped_roles(parser.root, markers))
        if len(blocks) != len(baseline.document.segments) or any(
            block[0] != segment.text
            for block, segment in zip(blocks, baseline.document.segments)
        ):
            raise AdapterContractError("Word role association changed extracted text")
        segments = tuple(
            replace(
                segment,
                role={"cover_position": "cover", "metadata": "instruction"}.get(
                    role, role
                ),
                role_confidence="medium" if role == "cover_position" else "high",
                role_basis=f"word_structure:{role}",
            )
            if role in _ROLES
            else segment
            for (_, role, _), segment in zip(blocks, baseline.document.segments)
        )
        return replace(baseline, document=replace(baseline.document, segments=segments))
