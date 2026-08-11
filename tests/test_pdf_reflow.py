from __future__ import annotations

from hhs_nofo_metrics.models import NormalizedDocument, Segment, SourceLocation
from hhs_nofo_metrics.pdf_reflow import METHOD_REFERENCE, reflow_flat_pdf_lines


def _segment(
    index: int,
    text: str,
    *,
    top: float,
    left: float = 72.0,
    role: str = "body",
) -> Segment:
    return Segment(
        id=f"line-{index}",
        text=text,
        location=SourceLocation(page=1, bbox=(left, top, 500.0, top + 12.0)),
        reading_order=index,
        role=role,
        role_confidence="low",
        role_basis="fixture",
        boundary_before="page" if index == 1 else "line",
    )


def test_flat_pdf_reflow_joins_wraps_but_preserves_block_boundaries() -> None:
    document = NormalizedDocument(
        source_kind="pdf",
        source_sha256="a" * 64,
        adapter_id="hhs-pdf-adapter",
        adapter_version="0.4.0",
        page_count=1,
        segments=(
            _segment(1, "Applicants must submit complete", top=100),
            _segment(2, "forms by the deadline.", top=114),
            _segment(3, "A distinct paragraph begins here.", top=144),
            _segment(4, "● A wrapped list item", top=174, role="list"),
            _segment(5, "continues on this line.", top=188, left=90),
        ),
    )

    result, diagnostics = reflow_flat_pdf_lines(document)

    assert [segment.text for segment in result.segments] == [
        "Applicants must submit complete forms by the deadline.",
        "A distinct paragraph begins here.",
        "● A wrapped list item continues on this line.",
    ]
    assert result.segments[-1].role == "list"
    assert diagnostics.paragraph_count == 3
    assert diagnostics.geometry_coverage == 1.0
    assert result.metadata["flat_pdf_reflow"]["method"] == METHOD_REFERENCE
