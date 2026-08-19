"""Minimal tagged-PDF structure and geometry observations.

This module is deliberately independent from metric policy, evidence ledgers,
and review overlays. It exposes only the source observations required by the
supported tagged-PDF adapter.
"""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping

import pdfplumber
from pypdf import PdfReader
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject

from hhs_nofo_metrics.errors import InputError

_PANEL_MINIMUM_WIDTH_RATIO = 0.12
_PANEL_MINIMUM_HEIGHT_POINTS = 24.0
_PANEL_MINIMUM_LEFT_RATIO = 0.70
_PANEL_PAGE_EDGE_TOLERANCE_POINTS = 1.0

_STRUCTURE_GROUP_TAGS = frozenset(
    {
        "P",
        "H",
        "H1",
        "H2",
        "H3",
        "H4",
        "H5",
        "H6",
        "H7",
        "Lbl",
        "LBody",
        "TH",
        "TD",
        "Caption",
        "Note",
        "TOCI",
    }
)
_STRUCTURE_GROUP_CONTAINERS = frozenset(
    {"Lbl", "LBody", "TH", "TD", "Caption", "Note", "TOCI"}
)


@dataclass(frozen=True, slots=True)
class ObservedWord:
    text: str
    left: float
    top: float
    right: float
    bottom: float
    font_name: str | None
    font_size: float | None
    native_index: int
    marked_content_id: int | None
    tag_path: tuple[str, ...]
    structure_rank: int | None
    structure_group_id: str | None
    structure_group_tag: str | None


@dataclass(frozen=True, slots=True)
class VisualLine:
    words: tuple[ObservedWord, ...]

    @property
    def text(self) -> str:
        return " ".join(word.text for word in self.words)

    @property
    def top(self) -> float:
        return min(word.top for word in self.words)

    @property
    def bottom(self) -> float:
        return max(word.bottom for word in self.words)


@dataclass(frozen=True, slots=True)
class PanelBoundary:
    left: float
    top: float
    right: float
    bottom: float


@dataclass(frozen=True, slots=True)
class TaggedContent:
    rank: int
    tag_path: tuple[str, ...]
    group_id: str
    group_tag: str


def dependency_versions() -> dict[str, str]:
    """Return the extraction dependencies published by the tagged adapter."""

    result = {}
    for distribution in ("pdfplumber", "pypdf"):
        try:
            result[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            result[distribution] = "unknown"
    return result


def _reference_key(value: Any) -> tuple[int, int] | None:
    reference = (
        value
        if isinstance(value, IndirectObject)
        else getattr(value, "indirect_reference", None)
    )
    if reference is None:
        return None
    return int(reference.idnum), int(reference.generation)


def tagged_content_by_page(
    path: Path,
    *,
    nested_container_groups: bool = False,
) -> tuple[dict[tuple[int, int], TaggedContent], str | None]:
    """Read page-local MCID paths and logical rank without requiring tags."""

    try:
        reader = PdfReader(path)
        catalog = reader.trailer["/Root"]
        root_reference = catalog.get("/StructTreeRoot")
        if root_reference is None:
            return {}, None
        root = root_reference.get_object()
        page_numbers = {
            _reference_key(page.indirect_reference): page_number
            for page_number, page in enumerate(reader.pages, start=1)
        }
        observed: dict[tuple[int, int], TaggedContent] = {}
        conflicts: set[tuple[int, int]] = set()
        rank = 0
        group_rank = 0

        def walk(
            node: Any,
            inherited_page: Any = None,
            tag_path: tuple[str, ...] = (),
            inherited_group: tuple[str, str] | None = None,
        ) -> None:
            nonlocal group_rank, rank
            value = node.get_object() if isinstance(node, IndirectObject) else node
            if isinstance(value, (ArrayObject, list, tuple)):
                for child in value:
                    walk(child, inherited_page, tag_path, inherited_group)
                return
            if isinstance(value, int):
                page_number = page_numbers.get(_reference_key(inherited_page))
                if page_number is not None:
                    key = (page_number, int(value))
                    if inherited_group is None:
                        return
                    tagged = TaggedContent(
                        rank=rank,
                        tag_path=tag_path,
                        group_id=inherited_group[0],
                        group_tag=inherited_group[1],
                    )
                    if key in observed and observed[key] != tagged:
                        conflicts.add(key)
                    else:
                        observed[key] = tagged
                    rank += 1
                return
            if not isinstance(value, (DictionaryObject, dict)):
                return
            page_reference = value.get("/Pg", inherited_page)
            tag = value.get("/S")
            next_path = tag_path
            tag_name = ""
            if tag is not None:
                tag_name = str(tag).removeprefix("/").strip()
                if tag_name:
                    next_path += (tag_name,)
            next_group = inherited_group
            nested_container = (
                nested_container_groups
                and inherited_group is not None
                and inherited_group[1] in _STRUCTURE_GROUP_CONTAINERS
                and tag_name in _STRUCTURE_GROUP_CONTAINERS
            )
            if tag_name in _STRUCTURE_GROUP_TAGS and (
                nested_container
                or inherited_group is None
                or inherited_group[1] not in _STRUCTURE_GROUP_CONTAINERS
            ):
                next_group = (f"structure-group-{group_rank}", tag_name)
                group_rank += 1
            if "/MCID" in value:
                page_number = page_numbers.get(_reference_key(page_reference))
                if page_number is not None and next_group is not None:
                    key = (page_number, int(value["/MCID"]))
                    tagged = TaggedContent(
                        rank=rank,
                        tag_path=next_path,
                        group_id=next_group[0],
                        group_tag=next_group[1],
                    )
                    if key in observed and observed[key] != tagged:
                        conflicts.add(key)
                    else:
                        observed[key] = tagged
                    rank += 1
            if "/K" in value:
                walk(value["/K"], page_reference, next_path, next_group)

        walk(root.get("/K"))
        for key in conflicts:
            observed.pop(key, None)
        return observed, None
    except Exception as exc:
        return {}, type(exc).__name__


def observed_words(
    page: pdfplumber.page.Page,
    tagged_content: Mapping[tuple[int, int], TaggedContent],
) -> tuple[ObservedWord, ...]:
    try:
        raw_words = page.extract_words(
            x_tolerance=2,
            y_tolerance=3,
            keep_blank_chars=False,
            use_text_flow=False,
            extra_attrs=["fontname", "size", "mcid", "tag"],
        )
    except Exception as exc:
        raise InputError(f"Unable to extract tagged PDF words: {exc}") from exc
    values: list[ObservedWord] = []
    for raw in raw_words:
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        native_index = len(values)
        try:
            left = float(raw["x0"])
            top = float(raw["top"])
            right = float(raw["x1"])
            bottom = float(raw["bottom"])
        except (KeyError, TypeError, ValueError) as exc:
            raise InputError("Extracted PDF word is missing valid geometry") from exc
        size_value = raw.get("size")
        try:
            font_size = float(size_value) if size_value is not None else None
        except (TypeError, ValueError):
            font_size = None
        font_name_value = raw.get("fontname")
        mcid_value = raw.get("mcid")
        try:
            marked_content_id = int(mcid_value) if mcid_value is not None else None
        except (TypeError, ValueError):
            marked_content_id = None
        tagged = (
            tagged_content.get((int(page.page_number), marked_content_id))
            if marked_content_id is not None
            else None
        )
        leaf_tag = str(raw.get("tag") or "").strip().removeprefix("/")
        values.append(
            ObservedWord(
                text=text,
                left=left,
                top=top,
                right=right,
                bottom=bottom,
                font_name=(str(font_name_value).strip() if font_name_value else None),
                font_size=font_size,
                native_index=native_index,
                marked_content_id=marked_content_id,
                tag_path=(
                    tagged.tag_path
                    if tagged is not None
                    else ((leaf_tag,) if leaf_tag else ())
                ),
                structure_rank=(tagged.rank if tagged is not None else None),
                structure_group_id=(tagged.group_id if tagged is not None else None),
                structure_group_tag=(tagged.group_tag if tagged is not None else None),
            )
        )
    return tuple(values)


def visual_lines(words: Iterable[ObservedWord]) -> tuple[VisualLine, ...]:
    groups: list[list[ObservedWord]] = []
    for word in sorted(
        words, key=lambda item: (item.top, item.left, item.native_index)
    ):
        group = next(
            (
                candidate
                for candidate in reversed(groups[-4:])
                if abs(median(item.top for item in candidate) - word.top) <= 3
            ),
            None,
        )
        if group is None:
            group = []
            groups.append(group)
        group.append(word)
    return tuple(
        VisualLine(
            tuple(sorted(group, key=lambda item: (item.left, item.native_index)))
        )
        for group in groups
    )


def right_bleed_panel_boundaries(
    page: pdfplumber.page.Page,
) -> tuple[PanelBoundary, ...]:
    """Observe large filled right-edge shapes without assigning semantics."""

    candidates: list[PanelBoundary] = []
    for item in (*page.rects, *page.curves):
        if not item.get("fill") or item.get("non_stroking_color") is None:
            continue
        try:
            boundary = PanelBoundary(
                left=float(item["x0"]),
                top=float(item["top"]),
                right=float(item["x1"]),
                bottom=float(item["bottom"]),
            )
        except (KeyError, TypeError, ValueError):
            continue
        width = boundary.right - boundary.left
        height = boundary.bottom - boundary.top
        if (
            width < float(page.width) * _PANEL_MINIMUM_WIDTH_RATIO
            or height < _PANEL_MINIMUM_HEIGHT_POINTS
            or boundary.left < float(page.width) * _PANEL_MINIMUM_LEFT_RATIO
            or boundary.right < float(page.width) - _PANEL_PAGE_EDGE_TOLERANCE_POINTS
        ):
            continue
        candidates.append(boundary)

    candidates.sort(
        key=lambda item: (
            -((item.right - item.left) * (item.bottom - item.top)),
            item.top,
            item.left,
        )
    )
    kept: list[PanelBoundary] = []
    for candidate in candidates:
        if any(
            candidate.left >= existing.left - 2
            and candidate.top >= existing.top - 2
            and candidate.right <= existing.right + 2
            and candidate.bottom <= existing.bottom + 2
            for existing in kept
        ):
            continue
        kept.append(candidate)
    return tuple(sorted(kept, key=lambda item: (item.top, item.left, item.bottom)))


def inside_panel(word: ObservedWord, panel: PanelBoundary) -> bool:
    center_x = (word.left + word.right) / 2
    center_y = (word.top + word.bottom) / 2
    return (
        panel.left <= center_x <= panel.right and panel.top <= center_y <= panel.bottom
    )


__all__ = [
    "ObservedWord",
    "PanelBoundary",
    "TaggedContent",
    "VisualLine",
    "dependency_versions",
    "inside_panel",
    "observed_words",
    "right_bleed_panel_boundaries",
    "tagged_content_by_page",
    "visual_lines",
]
