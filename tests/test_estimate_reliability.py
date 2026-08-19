from hhs_nofo_metrics.estimate_reliability import build_metric_reliability


def word_count_reliability(
    *,
    included: int,
    excluded: int,
    unknown_words: int,
    total_words: int = 1_000,
    failed_pages: int = 0,
):
    return build_metric_reliability(
        metric_id="word_count",
        included_unknown_value=included,
        excluded_unknown_value=excluded,
        classification_coverage=0.99,
        unknown_segment_count=1,
        unknown_word_count=unknown_words,
        total_observed_word_count=total_words,
        failed_page_count=failed_pages,
    )


def test_word_count_reliability_thresholds_are_versioned_behavior() -> None:
    high = word_count_reliability(
        included=1_000,
        excluded=995,
        unknown_words=5,
    )
    moderate = word_count_reliability(
        included=1_000,
        excluded=990,
        unknown_words=10,
    )
    low = word_count_reliability(
        included=1_000,
        excluded=950,
        unknown_words=50,
    )

    assert high.level == "high"
    assert moderate.level == "moderate"
    assert low.level == "low"
    assert high.method.id == "hhs-pdf-estimate-reliability"
    assert high.method.version == "0.2.0"


def test_failed_page_forces_low_reliability() -> None:
    reliability = word_count_reliability(
        included=1_000,
        excluded=1_000,
        unknown_words=0,
        failed_pages=1,
    )

    assert reliability.level == "low"
    assert "page_extraction_incomplete" in reliability.reason_codes


def test_readability_scores_use_absolute_not_relative_sensitivity() -> None:
    reliability = build_metric_reliability(
        metric_id="flesch_kincaid_grade_level",
        included_unknown_value=10.0,
        excluded_unknown_value=9.7,
        classification_coverage=0.99,
        unknown_segment_count=1,
        unknown_word_count=1,
        total_observed_word_count=1_000,
        failed_page_count=0,
    )

    assert reliability.level == "moderate"
    assert reliability.sensitivity.absolute_delta == 0.3


def test_passive_percentage_uses_percentage_point_sensitivity() -> None:
    reliability = build_metric_reliability(
        metric_id="passive_sentence_percentage",
        included_unknown_value=8.0,
        excluded_unknown_value=7.2,
        classification_coverage=0.99,
        unknown_segment_count=1,
        unknown_word_count=1,
        total_observed_word_count=1_000,
        failed_page_count=0,
    )

    assert reliability.level == "moderate"
    assert reliability.sensitivity.absolute_delta == 0.8
