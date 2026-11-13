"""Conservative Word front-matter recognition before HTML conversion.

This module operates on already parsed WordprocessingML, not raw ZIPs or
arbitrary HTML. Positions refer to children of the main document body.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Literal
from xml.dom import Node
from xml.dom.minidom import Document
from xml.etree.ElementTree import Element, fromstring

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_TOC_STYLE = re.compile(r"toc[1-9]", re.IGNORECASE)
_HEADING_STYLE = re.compile(r"heading[1-9]", re.IGNORECASE)
_TOC_INSTRUCTION = re.compile(r"^\s*TOC(?:\s|$)", re.IGNORECASE)
_INSTRUCTION_LABEL = re.compile(
    r"^(?:instructions for (?:nofo writers|template managers|new nofo team)\b|"
    r"[^\n]+?-specific instructions\b)",
    re.IGNORECASE,
)
_HEADING_LEVELS = frozenset(str(i) for i in range(9))


@dataclass(frozen=True, slots=True)
class WordFrontMatter:
    role: Literal["cover", "table_of_contents", "instruction", "metadata"]
    basis: Literal["gallery", "style", "field", "label", "position", "table", "builder"]


def _text(node: Element) -> str:
    return " ".join("".join(t.text or "" for t in node.iter(f"{_W}t")).split())


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


def _is_instruction_table(table: Element) -> bool:
    """Match the Builder instruction-table convention, not visual styling."""
    if table.tag != f"{_W}tbl":
        return False
    rows = table.findall(f"{_W}tr")
    if len(rows) != 1:
        return False
    cells = rows[0].findall(f"{_W}tc")
    if len(cells) != 1 or cells[0].find(f".//{_W}tbl") is not None:
        return False
    first = next(
        (
            " ".join("".join(t.text or "" for t in p.iter(f"{_W}t")).split())
            for p in cells[0].findall(f"{_W}p")
            if any((t.text or "").strip() for t in p.iter(f"{_W}t"))
        ),
        "",
    )
    return bool(_INSTRUCTION_LABEL.match(first))


def _is_simple_toc(paragraph: Element) -> bool:
    text_nodes = {
        node for node in paragraph.iter(f"{_W}t") if (node.text or "").strip()
    }
    return any(
        _TOC_INSTRUCTION.match(field.get(f"{_W}instr", ""))
        and text_nodes <= set(field.iter(f"{_W}t"))
        for field in paragraph.findall(f"{_W}fldSimple")
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
        if _is_instruction_table(block):
            roles[index] = WordFrontMatter("instruction", "table")
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
        if _is_simple_toc(block):
            roles[index] = WordFrontMatter("table_of_contents", "field")
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
    # A literal label alone is not sufficient. Match the generated Basic
    # information run, bounded by the next heading/non-paragraph.
    for index, block in enumerate(blocks):
        if not _is_heading(block) or _text(block).casefold() != "basic information":
            continue
        for end in range(index + 1, len(blocks)):
            if blocks[end].tag != f"{_W}p" or _is_heading(blocks[end]):
                break
        else:
            end = len(blocks)
        lines = [_text(item) for item in blocks[index + 1 : end]]
        if not lines or not lines[0].casefold().startswith("opdiv:"):
            continue
        if not any(line.casefold().startswith("opportunity number:") for line in lines):
            continue
        for position, line in enumerate(lines, index + 1):
            if re.match(r"^metadata (?:author|subject|keywords):\s*\S", line, re.I):
                roles.setdefault(position, WordFrontMatter("metadata", "builder"))
        break
    return roles


def mark_word_scope(
    body: Element, *, source_sha256: str, instruction_paragraphs: tuple[int, ...] = ()
) -> dict[str, str]:
    """Add paired bookmarks to a disposable, parsed conversion copy.

    The caller must convert the copy with user-supplied style mappings disabled.
    Names are deterministic for reproducibility and checked against every
    original bookmark in the body; new IDs cannot collide with source IDs.
    """
    used_names = {node.get(f"{_W}name") for node in body.iter(f"{_W}bookmarkStart")}
    used_ids = {
        node.get(f"{_W}id")
        for node in body.iter()
        if node.tag in {f"{_W}bookmarkStart", f"{_W}bookmarkEnd"}
    }
    salt = 0
    while True:
        prefix = (
            "scope_"
            + hashlib.sha256(f"{source_sha256}:{salt}".encode()).hexdigest()[:16]
        )
        if not any(name and name.startswith(prefix + "_") for name in used_names):
            break
        salt += 1
    markers = {}
    next_id = 0

    def bookmark(name: str) -> tuple[Element, Element]:
        nonlocal next_id
        while str(next_id) in used_ids:
            next_id += 1
        identifier = str(next_id)
        next_id += 1
        return (
            Element(f"{_W}bookmarkStart", {f"{_W}name": name, f"{_W}id": identifier}),
            Element(f"{_W}bookmarkEnd", {f"{_W}id": identifier}),
        )

    blocks = list(body)
    classifications = {}
    for index, classification in recognize_front_matter(body).items():
        role = (
            "cover_position"
            if classification.basis == "position"
            else classification.role
        )
        for paragraph in blocks[index].iter(f"{_W}p"):
            classifications[paragraph] = role
    paragraphs = list(body.iter(f"{_W}p"))
    for index in instruction_paragraphs:
        classifications[paragraphs[index]] = "instruction"
    for paragraph, role in classifications.items():
        # Don't annotate an outer paragraph containing nested textbox prose.
        if paragraph.find(f".//{_W}p") is not None:
            continue
        key = f"{prefix}_{len(markers)}"
        start, start_end = bookmark(key + "_s")
        end, end_end = bookmark(key + "_e")
        offset = 1 if len(paragraph) and paragraph[0].tag == f"{_W}pPr" else 0
        paragraph.insert(offset, start)
        paragraph.insert(offset + 1, start_end)
        paragraph.extend((end, end_end))
        markers[key] = role
    return markers


def mark_conversion_document(
    document: Document,
    *,
    source_sha256: str,
    instruction_paragraphs: tuple[int, ...] = (),
) -> dict[str, str]:
    """Mark a validated DOM without rewriting its namespace declarations."""
    namespace = _W[1:-1]
    bodies = document.getElementsByTagNameNS(namespace, "body")
    if len(bodies) != 1:
        return {}
    body = bodies[0]
    # Parse the whole document so declarations on the root are in scope.
    tree_body = fromstring(document.toxml()).find(f"{_W}body")
    if tree_body is None:
        return {}
    markers = mark_word_scope(
        tree_body,
        source_sha256=source_sha256,
        instruction_paragraphs=instruction_paragraphs,
    )
    if not markers:
        return {}
    for tree_p, dom_p in zip(
        tree_body.iter(f"{_W}p"),
        body.getElementsByTagNameNS(namespace, "p"),
        strict=True,
    ):
        for index, node in enumerate(tree_p):
            name = node.get(f"{_W}name", "")
            if not name.endswith(("_s", "_e")) or name[:-2] not in markers:
                continue
            prefix = dom_p.prefix
            start = document.createElementNS(
                namespace, f"{prefix}:bookmarkStart" if prefix else "bookmarkStart"
            )
            end = document.createElementNS(
                namespace, f"{prefix}:bookmarkEnd" if prefix else "bookmarkEnd"
            )
            # Word attributes need a namespace prefix even in a default-ns document.
            attr_prefix = prefix or "scopeWord"
            if not prefix:
                start.setAttribute("xmlns:scopeWord", namespace)
                end.setAttribute("xmlns:scopeWord", namespace)
            for marker in (start, end):
                marker.setAttributeNS(
                    namespace, f"{attr_prefix}:id", node.attrib[f"{_W}id"]
                )
            start.setAttributeNS(namespace, f"{attr_prefix}:name", name)
            elements = [
                child
                for child in dom_p.childNodes
                if child.nodeType == Node.ELEMENT_NODE
            ]
            reference = elements[index] if index < len(elements) else None
            dom_p.insertBefore(start, reference)
            dom_p.insertBefore(end, reference)
    return markers
