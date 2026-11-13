"""Conservative Word front-matter recognition before HTML conversion.

This module operates on already parsed WordprocessingML, not raw ZIPs or
arbitrary HTML. Positions refer to children of the main document body.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from xml.etree.ElementTree import Element

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_TOC_STYLE = re.compile(r"toc[1-9]", re.IGNORECASE)
_HEADING_STYLE = re.compile(r"heading[1-9]", re.IGNORECASE)
_TOC_INSTRUCTION = re.compile(r"^\s*TOC(?:\s|$)", re.IGNORECASE)
_HEADING_LEVELS = frozenset(str(i) for i in range(9))


@dataclass(frozen=True, slots=True)
class WordFrontMatter:
    role: Literal["cover", "table_of_contents"]
    basis: Literal["gallery", "style", "field", "label", "position"]


def _style(paragraph: Element) -> str:
    style = paragraph.find(f"{_W}pPr/{_W}pStyle")
    return style.get(f"{_W}val", "").replace(" ", "") if style is not None else ""


def _is_heading(paragraph: Element) -> bool:
    if paragraph.tag != f"{_W}p":
        return False
    level = paragraph.find(f"{_W}pPr/{_W}outlineLvl")
    return bool(_HEADING_STYLE.fullmatch(_style(paragraph))) or (
        level is not None and level.get(f"{_W}val") in _HEADING_LEVELS
    )


def recognize_front_matter(body: Element) -> dict[int, WordFrontMatter]:
    """Identify cover and TOC blocks, leaving ambiguous paragraphs countable."""
    if body.tag != f"{_W}body":
        raise ValueError("Expected a WordprocessingML body")
    blocks = list(body)
    roles: dict[int, WordFrontMatter] = {}
    # Track the complete outer field, including nested page-reference fields.
    # Never accept an unterminated field or exclude unrelated prose that shares
    # the opening/closing paragraph of a field.
    fields: list[tuple[int, list[str]]] = []
    for index, block in enumerate(blocks):
        if block.tag == f"{_W}sdt":
            gallery = block.find(f"{_W}sdtPr/{_W}docPartObj/{_W}docPartGallery")
            if gallery is not None:
                value = gallery.get(f"{_W}val", "").casefold()
                if value == "cover pages":
                    roles[index] = WordFrontMatter("cover", "gallery")
                elif value == "table of contents":
                    roles[index] = WordFrontMatter("table_of_contents", "gallery")
        if block.tag != f"{_W}p":
            fields.clear()
            continue
        if _TOC_STYLE.fullmatch(_style(block)):
            roles[index] = WordFrontMatter("table_of_contents", "style")
        for node in block.iter():
            if node.tag == f"{_W}fldChar":
                kind = node.get(f"{_W}fldCharType")
                if kind == "begin":
                    fields.append((index, []))
                elif kind == "end" and fields:
                    start, instruction = fields.pop()
                    if not fields and _TOC_INSTRUCTION.match("".join(instruction)):
                        for position in range(start + 1, index):
                            roles.setdefault(
                                position, WordFrontMatter("table_of_contents", "field")
                            )
            elif node.tag == f"{_W}instrText" and fields:
                fields[-1][1].append(node.text or "")

    for index, block in enumerate(blocks):
        if index in roles or block.tag != f"{_W}p":
            continue
        # Recognize the built-in TOC heading only beside actual TOC entries.
        next_role = roles.get(index + 1)
        if (
            _style(block).casefold() == "tocheading"
            and next_role is not None
            and next_role.role == "table_of_contents"
        ):
            roles[index] = WordFrontMatter("table_of_contents", "label")

    for index, block in enumerate(blocks[:-1]):
        if block.find(f"{_W}pPr/{_W}sectPr") is None:
            continue
        next_role = roles.get(index + 1)
        if (
            (next_role is not None and next_role.role == "table_of_contents")
            or _is_heading(blocks[index + 1])
        ) and not any(_is_heading(previous) for previous in blocks[: index + 1]):
            for position in range(index + 1):
                roles.setdefault(position, WordFrontMatter("cover", "position"))
        break
    return roles
