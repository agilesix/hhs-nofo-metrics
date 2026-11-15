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
# A leading cover section is short, unheaded, and made of labels, not prose.
_COVER_MAX_WORDS = 100
_COVER_MAX_PARAGRAPH_WORDS = 25
_TERMINAL_PUNCTUATION = re.compile(r"[.!?][\"'\u201d\u2019)\]]*$")
_COVER_SECTION_TAGS = frozenset({f"{_W}p", f"{_W}bookmarkStart", f"{_W}bookmarkEnd"})
_METADATA_HEADINGS = frozenset({"basic information", "before you begin"})


@dataclass(frozen=True, slots=True)
class WordFrontMatter:
    role: Literal[
        "cover", "cover_position", "table_of_contents", "instruction", "metadata"
    ]
    basis: Literal["gallery", "style", "field", "label", "table", "builder", "section"]


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


def _simple_toc_fields(paragraph: Element) -> list[Element]:
    return [
        field
        for field in paragraph.findall(f"{_W}fldSimple")
        if _TOC_INSTRUCTION.match(field.get(f"{_W}instr", ""))
    ]


def _leading_cover_section(
    blocks: list[Element], roles: dict[int, WordFrontMatter]
) -> tuple[int, ...]:
    """Return text paragraphs of an unmarked cover section, or nothing.

    Some exports (for example GrantSolutions Announcement Module Word files)
    place cover lines in plain paragraphs, end the first section, and start
    the next section with a table of contents. Recognize that layout only when
    the first section has no headings, no sentence-ending punctuation and few
    words, so opening applicant prose before a section break stays countable.
    """
    end = None
    for index, block in enumerate(blocks):
        if block.tag not in _COVER_SECTION_TAGS or index in roles:
            return ()
        if block.tag == f"{_W}p" and block.find(f"{_W}pPr/{_W}sectPr") is not None:
            end = index
            break
    if end is None:
        return ()
    following = [
        index
        for index in range(end + 1, len(blocks))
        if blocks[index].tag != f"{_W}p" or _text(blocks[index])
    ]
    if not following:
        return ()

    def is_toc(position: int) -> bool:
        role = roles.get(position)
        return role is not None and role.role == "table_of_contents"

    # Allow one unrecognized label paragraph (for example "Table of Contents")
    # directly before the first recognized contents entry.
    if not (
        is_toc(following[0])
        or (
            blocks[following[0]].tag == f"{_W}p"
            and len(following) > 1
            and is_toc(following[1])
        )
    ):
        return ()
    paragraphs = [
        (index, _text(block))
        for index, block in enumerate(blocks[: end + 1])
        if block.tag == f"{_W}p"
    ]
    lines = [(index, text) for index, text in paragraphs if text]
    if not lines or any(_is_heading(blocks[index]) for index, _ in paragraphs):
        return ()
    word_counts = [len(text.split()) for _, text in lines]
    if (
        sum(word_counts) > _COVER_MAX_WORDS
        or max(word_counts) > _COVER_MAX_PARAGRAPH_WORDS
        or any(_TERMINAL_PUNCTUATION.search(text) for _, text in lines)
    ):
        return ()
    return tuple(index for index, _ in lines)


def recognize_front_matter(body: Element) -> dict[int, WordFrontMatter]:
    """Identify cover and TOC blocks, leaving ambiguous paragraphs countable."""
    if body.tag != f"{_W}body":
        raise ValueError("Expected a WordprocessingML body")
    blocks = list(body)
    roles: dict[int, WordFrontMatter] = {}
    # Track the complete outer field, including nested page-reference fields.
    # Never accept an unterminated field or exclude unrelated prose that shares
    # the opening/closing paragraph of a field.
    fields: list[list[str]] = []
    result_start = None
    result_paragraphs: set[int] = set()
    outside_text: set[int] = set()
    completed_toc_paragraphs: set[int] = set()
    mixed_toc_paragraphs: set[int] = set()
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
            result_start = None
            result_paragraphs.clear()
            continue
        if _TOC_STYLE.fullmatch(_style(block)):
            roles[index] = WordFrontMatter("table_of_contents", "style")
        simple_fields = _simple_toc_fields(block)
        if simple_fields:
            text_nodes = {
                node for node in block.iter(f"{_W}t") if (node.text or "").strip()
            }
            if any(text_nodes <= set(field.iter(f"{_W}t")) for field in simple_fields):
                roles[index] = WordFrontMatter("table_of_contents", "field")
            else:
                mixed_toc_paragraphs.add(index)
        for node in block.iter():
            if node.tag == f"{_W}fldChar":
                kind = node.get(f"{_W}fldCharType")
                if kind == "begin":
                    if not fields:
                        result_start = None
                        result_paragraphs.clear()
                    fields.append([])
                elif kind == "separate" and len(fields) == 1:
                    if _TOC_INSTRUCTION.match("".join(fields[0])):
                        result_start = index
                elif kind == "end" and fields:
                    fields.pop()
                    if not fields and result_start is not None:
                        completed_toc_paragraphs.update(result_paragraphs)
                        result_start = None
            elif node.tag == f"{_W}instrText" and fields:
                fields[-1].append(node.text or "")
            elif node.tag == f"{_W}t" and (node.text or "").strip():
                if result_start is not None:
                    result_paragraphs.add(index)
                else:
                    outside_text.add(index)

    # Field boundaries take precedence over the paragraph style.
    mixed_toc_paragraphs.update(completed_toc_paragraphs & outside_text)
    for position in completed_toc_paragraphs - outside_text:
        roles.setdefault(position, WordFrontMatter("table_of_contents", "field"))
    for position in mixed_toc_paragraphs:
        roles.pop(position, None)

    for index, block in enumerate(blocks):
        if index in roles or index in mixed_toc_paragraphs or block.tag != f"{_W}p":
            continue
        # Recognize the built-in TOC heading only beside actual TOC entries.
        next_role = roles.get(index + 1)
        if (
            _style(block).casefold() == "tocheading"
            and next_role is not None
            and next_role.role == "table_of_contents"
        ):
            roles[index] = WordFrontMatter("table_of_contents", "label")

    for index in _leading_cover_section(blocks, roles):
        roles[index] = WordFrontMatter("cover_position", "section")

    # A literal label alone is not sufficient. Match the generated Basic
    # information run (titled "Before You Begin" in some exports), bounded by
    # the next heading/non-paragraph.
    for index, block in enumerate(blocks):
        if not _is_heading(block) or _text(block).casefold() not in _METADATA_HEADINGS:
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
        for paragraph in blocks[index].iter(f"{_W}p"):
            classifications[paragraph] = classification.role
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
