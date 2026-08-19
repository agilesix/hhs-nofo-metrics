"""Local, page-preserving PDF adapter."""

from __future__ import annotations

import hashlib
import importlib.metadata
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pdfplumber
from pypdf import PdfReader

from hhs_nofo_metrics.classification.repeated_edges import (
    METHOD_ID as EDGE_METHOD_ID,
)
from hhs_nofo_metrics.classification.repeated_edges import (
    METHOD_VERSION as EDGE_METHOD_VERSION,
)
from hhs_nofo_metrics.classification.repeated_edges import (
    find_repeated_edge_patterns,
    is_page_edge,
    normalize_edge_text,
)
from hhs_nofo_metrics.errors import InputError
from hhs_nofo_metrics.models import (
    OBSERVED_PDF_METADATA_FIELDS,
    NormalizedDocument,
    Segment,
    SourceLocation,
)

ADAPTER_ID = "hhs-pdf-adapter"
ADAPTER_VERSION = "0.4.0"
_LIST_RE = re.compile(r"^\s*(?:[•●▪◦◻☐☑□*-]|o|\(?\d{1,3}[.)])\s+")
_TOC_RE = re.compile(r"\.{3,}\s*\d+\s*$")
_PAGE_NUMBER_RE = re.compile(r"^(?:page\s+)?\d+(?:\s+of\s+\d+)?$", re.I)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _classify_line(
    line: str,
    *,
    page: int,
    page_count: int,
    index: int,
    line_count: int,
    repeated_patterns: dict[str, int],
) -> tuple[str, str, str]:
    normalized_edge = normalize_edge_text(line)
    if (
        is_page_edge(index, line_count, edge_line_count=1)
        and normalized_edge in repeated_patterns
    ):
        if index < 1:
            return "header", "high", f"{EDGE_METHOD_ID}@{EDGE_METHOD_VERSION}"
        return "footer", "high", f"{EDGE_METHOD_ID}@{EDGE_METHOD_VERSION}"
    if _PAGE_NUMBER_RE.fullmatch(line.casefold()):
        return "navigation", "high", "page-number-pattern@1.0.0"
    if _TOC_RE.search(line):
        return "table_of_contents", "high", "dot-leader-pattern@1.0.0"
    if _LIST_RE.match(line):
        return "list", "high", "list-prefix-pattern@1.2.0"
    words = re.findall(r"[A-Za-z]+", line)
    if (
        words
        and len(words) <= 10
        and len(line) <= 80
        and not line.endswith((".", "?", "!", ";", ":"))
        and (line.istitle() or line.isupper())
    ):
        return "heading", "medium", "bounded-heading-shape@1.0.0"
    if page == 1 and index < 4:
        return "cover", "low", "first-page-position@1.0.0"
    return "body", "low", "pdf-line-default@1.0.0"


def _metadata(reader: PdfReader) -> dict[str, str]:
    metadata = reader.metadata or {}
    observed: dict[str, str] = {}
    for key, value in metadata.items():
        normalized_key = str(key).lstrip("/")
        if value is not None and normalized_key in OBSERVED_PDF_METADATA_FIELDS:
            observed[normalized_key] = str(value)
    return observed


def _line_geometry(
    page: pdfplumber.page.Page,
    lines: list[str],
) -> list[tuple[float, float, float, float] | None]:
    """Align optional pdfplumber line geometry without changing extracted text."""

    try:
        observed = page.extract_text_lines(
            strip=True,
            return_chars=False,
            x_tolerance=2,
            y_tolerance=3,
        )
    except Exception:
        return [None] * len(lines)
    geometry_lines: list[str] = []
    geometry_boxes: list[tuple[float, float, float, float]] = []
    for item in observed:
        text = _normalize_line(str(item.get("text") or ""))
        if not text:
            continue
        try:
            box = (
                float(item["x0"]),
                float(item["top"]),
                float(item["x1"]),
                float(item["bottom"]),
            )
        except (KeyError, TypeError, ValueError):
            continue
        geometry_lines.append(text)
        geometry_boxes.append(box)

    aligned: list[tuple[float, float, float, float] | None] = [None] * len(lines)
    matcher = SequenceMatcher(a=lines, b=geometry_lines, autojunk=False)
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            aligned[block.a + offset] = geometry_boxes[block.b + offset]
    return aligned


class PdfAdapter:
    id = ADAPTER_ID
    version = ADAPTER_VERSION

    def extract(self, source: Path) -> NormalizedDocument:
        path = source.expanduser().resolve()
        if not path.is_file():
            raise InputError(f"PDF not found: {path}")
        if path.suffix.casefold() != ".pdf":
            raise InputError(f"Input must be a PDF: {path}")
        with path.open("rb") as stream:
            if b"%PDF-" not in stream.read(1024):
                raise InputError("Input does not contain a PDF header")

        page_lines: list[list[str]] = []
        page_line_geometry: list[list[tuple[float, float, float, float] | None]] = []
        extraction_errors: list[int] = []
        try:
            with pdfplumber.open(path) as pdf:
                for page_number, page in enumerate(pdf.pages, start=1):
                    try:
                        text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                    except Exception:
                        text = ""
                        extraction_errors.append(page_number)
                    lines = [
                        normalized
                        for raw in text.splitlines()
                        if (normalized := _normalize_line(raw))
                    ]
                    page_lines.append(lines)
                    page_line_geometry.append(_line_geometry(page, lines))
        except Exception as exc:
            raise InputError(f"Unable to extract PDF text: {exc}") from exc

        repeated = find_repeated_edge_patterns(page_lines, edge_line_count=1)
        textless_pages = [
            page_number
            for page_number, lines in enumerate(page_lines, start=1)
            if not lines
        ]
        segments: list[Segment] = []
        reading_order = 0
        page_count = len(page_lines)
        for page_number, lines in enumerate(page_lines, start=1):
            boxes = page_line_geometry[page_number - 1]
            for line_index, line in enumerate(lines):
                role, confidence, basis = _classify_line(
                    line,
                    page=page_number,
                    page_count=page_count,
                    index=line_index,
                    line_count=len(lines),
                    repeated_patterns=repeated,
                )
                reading_order += 1
                segments.append(
                    Segment(
                        id=f"p{page_number:04d}-l{line_index + 1:04d}",
                        text=line,
                        location=SourceLocation(
                            page=page_number,
                            bbox=boxes[line_index],
                        ),
                        reading_order=reading_order,
                        role=role,
                        role_confidence=confidence,
                        role_basis=basis,
                        boundary_before="page" if line_index == 0 else "line",
                    )
                )

        try:
            reader = PdfReader(path)
            observed_metadata = _metadata(reader)
        except Exception:
            observed_metadata = {}
        warnings = tuple(
            [f"text_extraction_failed_page:{page}" for page in extraction_errors]
            + (["no_text_segments_extracted"] if not segments else [])
        )
        metadata: dict[str, Any] = {
            "observed_pdf_metadata": observed_metadata,
            "extraction_error_pages": extraction_errors,
            "textless_pages": textless_pages,
            "repeated_edge_patterns": len(repeated),
            "line_geometry": {
                "matched_line_count": sum(
                    box is not None for boxes in page_line_geometry for box in boxes
                ),
                "total_line_count": sum(len(lines) for lines in page_lines),
                "method": "pdfplumber-extract-text-lines-sequence-alignment@1.0.0",
            },
            "dependencies": {
                "pdfplumber": importlib.metadata.version("pdfplumber"),
                "pypdf": importlib.metadata.version("pypdf"),
            },
        }
        return NormalizedDocument(
            source_kind="pdf",
            source_sha256=sha256_file(path),
            adapter_id=self.id,
            adapter_version=self.version,
            segments=tuple(segments),
            page_count=page_count,
            warnings=warnings,
            metadata=metadata,
        )
