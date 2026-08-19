from __future__ import annotations

import pytest

from hhs_nofo_metrics.resolved_scope import (
    RESOLVED_SCOPE_CONTRACT_VERSION,
    ResolvedMeasurementScope,
    calculate_resolved_measurement_scope,
)


def test_shared_kernel_calculates_document_and_readability_scopes() -> None:
    scope = ResolvedMeasurementScope(
        document_status="eligible",
        readability_status="eligible",
        document_content_units=(
            "Funding opportunity",
            "Applicants submit forms. Reviewers score applications.",
        ),
        readability_sentences=(
            "Applicants submit forms.",
            "Reviewers score applications.",
        ),
    )

    calculation = calculate_resolved_measurement_scope(scope)

    assert RESOLVED_SCOPE_CONTRACT_VERSION == "0.1.0-internal"
    assert calculation.document_word_count == 8
    assert calculation.readability_counts is not None
    assert calculation.readability_counts.readability_word_count == 6
    assert calculation.readability_counts.sentence_count == 2
    assert calculation.readability_metrics["words_per_sentence"] == 3
    assert calculation.readability_metrics["flesch_kincaid_grade_level"] is not None


def test_same_resolved_scope_is_source_neutral() -> None:
    html_scope = ResolvedMeasurementScope(
        document_status="eligible",
        readability_status="eligible",
        document_content_units=("Applicants submit a complete plan.",),
        readability_sentences=("Applicants submit a complete plan.",),
    )
    pdf_scope = ResolvedMeasurementScope(
        document_status="eligible",
        readability_status="eligible",
        document_content_units=("Applicants submit a complete plan.",),
        readability_sentences=("Applicants submit a complete plan.",),
    )

    assert calculate_resolved_measurement_scope(
        html_scope
    ) == calculate_resolved_measurement_scope(pdf_scope)


def test_incomplete_scopes_fail_closed_without_retaining_text() -> None:
    calculation = calculate_resolved_measurement_scope(
        ResolvedMeasurementScope(
            document_status="provisional",
            readability_status="unable",
        )
    )

    assert calculation.document_word_count is None
    assert calculation.readability_counts is None
    assert not calculation.readability_metrics

    with pytest.raises(ValueError, match="cannot carry content"):
        ResolvedMeasurementScope(
            document_status="provisional",
            readability_status="unable",
            document_content_units=("Unresolved private text",),
        )
