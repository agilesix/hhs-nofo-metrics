from __future__ import annotations

import pytest

from hhs_nofo_metrics.adapters.pdf import _classify_line


def classify(line: str) -> tuple[str, str, str]:
    return _classify_line(
        line,
        page=2,
        page_count=3,
        index=3,
        line_count=10,
        repeated_patterns={},
    )


@pytest.mark.parametrize(
    "line",
    (
        "o Include a detailed work plan.",
        "  o Name and title",
        "◦ Detect health threats early.",
        " Attachment 3: Evaluation plan",
        " Hospital signature and date",
    ),
)
def test_pdf_adapter_recognizes_reviewed_list_markers(line: str) -> None:
    assert classify(line) == ("list", "high", "list-prefix-pattern@1.2.0")


@pytest.mark.parametrize(
    "line",
    (
        "otherwise submit the application.",
        "O Applicants must submit a plan.",
    ),
)
def test_pdf_adapter_keeps_o_recognition_bounded(line: str) -> None:
    assert classify(line)[0] != "list"
