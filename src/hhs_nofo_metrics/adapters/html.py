"""Deterministic semantic-HTML adapter for source-native NOFO metrics."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Mapping

from hhs_nofo_metrics.errors import AdapterContractError
from hhs_nofo_metrics.models import NormalizedDocument, Segment, SourceLocation
from hhs_nofo_metrics.sources import MaterializedSourceBundle
from hhs_nofo_metrics.version import PACKAGE_VERSION

from .contracts import (
    AdapterCoverage,
    AdapterDescriptor,
    AdapterEvidence,
    AdapterResult,
    JsonValue,
    SupportAssessment,
)

ADAPTER_ID = "hhs-semantic-html-adapter"
ADAPTER_VERSION = "0.1.1"

_WHITESPACE_RE = re.compile(r"\s+")
_VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_SKIP_TAGS = frozenset({"script", "style", "noscript", "svg", "template"})
_BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "dd",
        "details",
        "dialog",
        "caption",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "h7",
        "header",
        "hr",
        "legend",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "summary",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    }
)
_HEADING_TAGS = frozenset(
    {
        "caption",
        "dt",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "h7",
        "legend",
        "summary",
        "th",
    }
)
_TEXT_BLOCK_TAGS = frozenset({"p", "blockquote", "dd", "figcaption", "pre"})
_P_IMPLIED_CLOSE_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "div",
        "dl",
        "fieldset",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "ul",
    }
)
_SAME_FAMILY_IMPLIED_CLOSE = {
    "li": frozenset({"li"}),
    "dt": frozenset({"dt", "dd"}),
    "dd": frozenset({"dt", "dd"}),
    "tr": frozenset({"tr"}),
    "td": frozenset({"td", "th"}),
    "th": frozenset({"td", "th"}),
    "thead": frozenset({"thead", "tbody", "tfoot"}),
    "tbody": frozenset({"thead", "tbody", "tfoot"}),
    "tfoot": frozenset({"thead", "tbody", "tfoot"}),
    "option": frozenset({"option"}),
    "optgroup": frozenset({"optgroup"}),
}
_IMPLIED_CLOSE_SCOPE_BARRIERS = {
    "li": frozenset({"menu", "ol", "ul"}),
    "dt": frozenset({"dl"}),
    "dd": frozenset({"dl"}),
    "tr": frozenset({"table"}),
    "td": frozenset({"table", "tr"}),
    "th": frozenset({"table", "tr"}),
    "thead": frozenset({"table"}),
    "tbody": frozenset({"table"}),
    "tfoot": frozenset({"table"}),
    "option": frozenset({"datalist", "optgroup", "select"}),
    "optgroup": frozenset({"datalist", "select"}),
}


@dataclass(slots=True)
class _Node:
    tag: str
    attrs: dict[str, str]
    children: list["_Node | str"] = field(default_factory=list)


class _DomParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("document", {})
        self._stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        requested = tag.casefold()
        implied_close = _SAME_FAMILY_IMPLIED_CLOSE.get(requested, frozenset())
        if requested in _P_IMPLIED_CLOSE_TAGS:
            implied_close = implied_close | {"p"}
        if implied_close:
            barriers = _IMPLIED_CLOSE_SCOPE_BARRIERS.get(requested, frozenset())
            for index in range(len(self._stack) - 1, 0, -1):
                if self._stack[index].tag in implied_close:
                    del self._stack[index:]
                    break
                if self._stack[index].tag in barriers:
                    break
        node = _Node(requested, {key.casefold(): value or "" for key, value in attrs})
        self._stack[-1].children.append(node)
        if node.tag not in _VOID_TAGS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.casefold() not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        requested = tag.casefold()
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == requested:
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        self._stack[-1].children.append(data)


def _normalized_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.replace("\xa0", " ")).strip()


def _is_hidden(node: _Node) -> bool:
    style = node.attrs.get("style", "").replace(" ", "").casefold()
    return (
        "hidden" in node.attrs
        or node.attrs.get("aria-hidden", "").casefold() == "true"
        or "display:none" in style
        or "visibility:hidden" in style
    )


def _inline_text(item: _Node | str) -> str:
    if isinstance(item, str):
        return item
    if item.tag in _SKIP_TAGS or _is_hidden(item) or item.tag in {"img", "input", "hr"}:
        return ""
    if item.tag == "br":
        return " "
    return "".join(_inline_text(child) for child in item.children)


def _find_by_id(node: _Node, root_id: str) -> _Node | None:
    if node.attrs.get("id") == root_id:
        return node
    for child in node.children:
        if isinstance(child, _Node) and (found := _find_by_id(child, root_id)):
            return found
    return None


def _context_role(node: _Node, inherited: str) -> str:
    if inherited in {"navigation", "header", "footer"}:
        return inherited
    if node.tag == "nav":
        return "navigation"
    if node.tag == "header":
        return "header"
    if node.tag == "footer":
        return "footer"
    if node.tag == "li":
        return "list"
    if node.tag in {"td", "th"}:
        return "table"
    return inherited


def _semantic_blocks(root: _Node) -> list[tuple[str, str, str]]:
    blocks: list[tuple[str, str, str]] = []

    def emit(text: str, role: str, tag: str) -> None:
        normalized = _normalized_text(text)
        if normalized:
            blocks.append((normalized, role, tag))

    def walk_children(node: _Node, role: str) -> None:
        inline: list[_Node | str] = []

        def flush() -> None:
            if inline:
                emit("".join(_inline_text(item) for item in inline), role, node.tag)
                inline.clear()

        for child in node.children:
            if isinstance(child, str) or child.tag not in _BLOCK_TAGS:
                inline.append(child)
            else:
                flush()
                walk(child, role)
        flush()

    def walk(node: _Node, inherited_role: str = "body") -> None:
        if node.tag in _SKIP_TAGS or _is_hidden(node):
            return
        role = _context_role(node, inherited_role)
        if node.tag in _HEADING_TAGS:
            emit(
                _inline_text(node),
                role if role in {"navigation", "header", "footer"} else "heading",
                node.tag,
            )
            return
        if node.tag in _TEXT_BLOCK_TAGS:
            emit(_inline_text(node), role, node.tag)
            return
        walk_children(node, role)

    walk(root)
    return blocks


class HtmlAdapterPlugin:
    descriptor = AdapterDescriptor(
        id=ADAPTER_ID,
        version=ADAPTER_VERSION,
        source_kinds=("html",),
        capabilities=frozenset({"text", "logical_roles", "reading_order"}),
        distribution="hhs-nofo-metrics",
        distribution_version=PACKAGE_VERSION,
    )

    def inspect_support(self, source: MaterializedSourceBundle) -> SupportAssessment:
        if source.primary.kind != "html":
            return SupportAssessment(
                status="unsupported",
                reason=f"Primary artifact kind is {source.primary.kind}, not html.",
            )
        try:
            sample = source.primary.path.read_bytes()[:4096]
            text = sample.decode("utf-8")
        except UnicodeDecodeError:
            return SupportAssessment(
                status="unsupported", reason="Primary HTML artifact is not UTF-8."
            )
        except OSError as exc:
            return SupportAssessment(status="indeterminate", reason=str(exc))
        if "<" not in text or ">" not in text:
            return SupportAssessment(
                status="unsupported", reason="Primary artifact has no HTML markup."
            )
        return SupportAssessment(
            status="supported",
            evidence=(
                AdapterEvidence(
                    code="utf8_html_markup", value="observed", confidence="high"
                ),
            ),
        )

    def extract(
        self,
        source: MaterializedSourceBundle,
        *,
        config: Mapping[str, JsonValue],
    ) -> AdapterResult:
        if source.auxiliaries:
            raise AdapterContractError(
                "hhs-semantic-html-adapter does not accept auxiliary artifacts"
            )
        unsupported = set(config) - {"root_id"}
        if unsupported:
            raise AdapterContractError(
                "Unsupported HTML adapter configuration: "
                + ", ".join(sorted(unsupported))
            )
        root_id = config.get("root_id")
        if root_id is not None and (
            not isinstance(root_id, str) or not root_id.strip()
        ):
            raise AdapterContractError(
                "HTML adapter root_id must be a non-empty string"
            )
        try:
            html = source.primary.path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise AdapterContractError("Primary HTML artifact is not UTF-8") from exc
        parser = _DomParser()
        parser.feed(html)
        parser.close()
        root = parser.root
        if root_id is not None:
            selected = _find_by_id(root, root_id)
            if selected is None:
                raise AdapterContractError(f"HTML root_id '{root_id}' was not found")
            root = selected
        blocks = _semantic_blocks(root)
        segments = tuple(
            Segment(
                id=hashlib.sha256(
                    f"{source.primary.sha256}:{index}:{tag}:{role}:{value}".encode(
                        "utf-8"
                    )
                ).hexdigest()[:24],
                text=value,
                location=SourceLocation(),
                reading_order=index,
                role=role,
                role_confidence="high",
                role_basis=f"semantic_html:{tag}",
                boundary_before="paragraph",
            )
            for index, (value, role, tag) in enumerate(blocks)
        )
        return AdapterResult(
            document=NormalizedDocument(
                source_kind="html",
                source_sha256=source.primary.sha256,
                adapter_id=self.descriptor.id,
                adapter_version=self.descriptor.version,
                segments=segments,
                metadata={"root_id": root_id or "document"},
            ),
            artifacts_consumed=("primary",),
            capabilities_used=self.descriptor.capabilities,
            coverage=AdapterCoverage(status="complete", matched_blocks=len(segments)),
            evidence=(
                AdapterEvidence(
                    code="semantic_html_blocks",
                    value=str(len(segments)),
                    confidence="high",
                ),
            ),
        )


__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "HtmlAdapterPlugin"]
