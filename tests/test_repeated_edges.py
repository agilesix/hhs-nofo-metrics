from hhs_nofo_metrics.classification.repeated_edges import (
    find_repeated_edge_patterns,
    normalize_edge_text,
)


def test_repeated_edge_detection_labels_without_rewriting_text() -> None:
    pages = [
        [f"Notice 2026 — Page {page}", "Unique body text", "Footer"]
        for page in range(1, 5)
    ]

    patterns = find_repeated_edge_patterns(pages)

    assert patterns["notice # — page #"] == 4
    assert patterns["footer"] == 4
    assert pages[0][0] == "Notice 2026 — Page 1"


def test_normalization_collapses_whitespace_and_digit_runs() -> None:
    assert normalize_edge_text("  NOFO  2026-001 ") == "nofo #-#"
