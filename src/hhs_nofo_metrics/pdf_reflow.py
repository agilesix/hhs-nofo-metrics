"""Conservative paragraph reconstruction for flat PDF text lines."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from statistics import median

from hhs_nofo_metrics.models import NormalizedDocument, Segment, SourceLocation

METHOD_ID = "hhs-flat-pdf-paragraph-reconstruction"
METHOD_VERSION = "0.1.0"
METHOD_REFERENCE = f"{METHOD_ID}@{METHOD_VERSION}"

_BLOCK_START_ROLES = frozenset(
    {
        "heading",
        "table",
        "cover",
        "table_of_contents",
        "instruction",
        "header",
        "footer",
        "navigation",
        "decorative",
    }
)


@dataclass(frozen=True, slots=True)
class ReflowDiagnostics:
    paragraph_count: int
    source_line_count: int
    geometry_line_count: int
    decision_counts: dict[str, int]

    @property
    def geometry_coverage(self) -> float:
        if not self.source_line_count:
            return 0.0
        return self.geometry_line_count / self.source_line_count

    def to_dict(self) -> dict[str, object]:
        return {
            "method": METHOD_REFERENCE,
            "paragraph_count": self.paragraph_count,
            "source_line_count": self.source_line_count,
            "geometry_line_count": self.geometry_line_count,
            "geometry_coverage": round(self.geometry_coverage, 6),
            "decision_counts": dict(sorted(self.decision_counts.items())),
        }


def _page_line_heights(segments: tuple[Segment, ...]) -> dict[int, float]:
    by_page: dict[int, list[float]] = {}
    for segment in segments:
        page = segment.location.page
        box = segment.location.bbox
        if page is None or box is None:
            continue
        height = box[3] - box[1]
        if height > 0:
            by_page.setdefault(page, []).append(height)
    return {page: median(values) for page, values in by_page.items() if values}


def _boundary_reason(
    previous: Segment,
    current: Segment,
    *,
    typical_height: float,
) -> str:
    if current.location.page != previous.location.page:
        return "page"
    if current.role == "list":
        return "list_item"
    if current.role in _BLOCK_START_ROLES or previous.role in _BLOCK_START_ROLES:
        return "structural_role"
    previous_box = previous.location.bbox
    current_box = current.location.bbox
    if previous_box is None or current_box is None:
        return "missing_geometry"

    horizontal_shift = abs(current_box[0] - previous_box[0])
    allowed_shift = 24.0 if previous.role == "list" and current.role == "body" else 14.0
    if horizontal_shift > allowed_shift:
        return "horizontal_shift"

    vertical_gap = current_box[1] - previous_box[3]
    if vertical_gap < -(0.35 * typical_height):
        return "overlapping_or_reordered_lines"
    if vertical_gap > max(8.0, 0.8 * typical_height):
        return "vertical_gap"
    return "continuation"


def _union_bbox(
    segments: tuple[Segment, ...],
) -> tuple[float, float, float, float] | None:
    boxes = [segment.location.bbox for segment in segments]
    if not boxes or any(box is None for box in boxes):
        return None
    present = [box for box in boxes if box is not None]
    return (
        min(box[0] for box in present),
        min(box[1] for box in present),
        max(box[2] for box in present),
        max(box[3] for box in present),
    )


def reflow_flat_pdf_lines(
    document: NormalizedDocument,
) -> tuple[NormalizedDocument, ReflowDiagnostics]:
    """Join visually continuous lines without claiming true PDF semantics.

    The transformation is intentionally conservative: it never reorders text,
    never joins across pages, and starts a new block when geometry or role
    evidence is insufficient. The result supports a low-confidence fallback,
    not an authoritative HTML or tagged-PDF measurement.
    """

    ordered = tuple(sorted(document.segments, key=lambda item: item.reading_order))
    if not ordered:
        diagnostics = ReflowDiagnostics(0, 0, 0, {})
        return document, diagnostics

    page_heights = _page_line_heights(ordered)
    counts: Counter[str] = Counter()
    groups: list[list[Segment]] = []
    for segment in ordered:
        if not groups:
            groups.append([segment])
            counts["document_start"] += 1
            continue
        previous = groups[-1][-1]
        typical_height = page_heights.get(segment.location.page or -1, 11.0)
        reason = _boundary_reason(previous, segment, typical_height=typical_height)
        counts[reason] += 1
        if reason == "continuation":
            groups[-1].append(segment)
        else:
            groups.append([segment])

    paragraphs: list[Segment] = []
    for index, values in enumerate(groups, start=1):
        group = tuple(values)
        first = group[0]
        role = first.role
        confidence = first.role_confidence
        basis = first.role_basis
        if len({segment.role for segment in group}) > 1:
            confidence = "low"
            basis = METHOD_REFERENCE
        paragraphs.append(
            Segment(
                id=f"flat-pdf-block-{index:05d}",
                text=" ".join(segment.text.strip() for segment in group),
                location=SourceLocation(
                    page=first.location.page,
                    bbox=_union_bbox(group),
                ),
                reading_order=index,
                role=role,
                role_confidence=confidence,
                role_basis=basis,
                boundary_before="page" if index == 1 else "paragraph",
            )
        )

    diagnostics = ReflowDiagnostics(
        paragraph_count=len(paragraphs),
        source_line_count=len(ordered),
        geometry_line_count=sum(
            segment.location.bbox is not None for segment in ordered
        ),
        decision_counts=dict(counts),
    )
    metadata = dict(document.metadata)
    metadata["flat_pdf_reflow"] = diagnostics.to_dict()
    return (
        NormalizedDocument(
            source_kind=document.source_kind,
            source_sha256=document.source_sha256,
            adapter_id=document.adapter_id,
            adapter_version=document.adapter_version,
            segments=tuple(paragraphs),
            page_count=document.page_count,
            warnings=document.warnings,
            metadata=metadata,
        ),
        diagnostics,
    )


__all__ = [
    "METHOD_ID",
    "METHOD_REFERENCE",
    "METHOD_VERSION",
    "ReflowDiagnostics",
    "reflow_flat_pdf_lines",
]
