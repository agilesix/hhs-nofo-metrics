from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from hhs_nofo_metrics.analysis_pipelines import (
    pipeline_reference_for_profile,
    resolve_profile_pipeline,
)
from hhs_nofo_metrics.errors import ProfileError
from hhs_nofo_metrics.models import (
    METRIC_IDS,
    AdapterIdentity,
    AnalysisPipelineConfiguration,
    AnalysisResult,
    CoverageSummary,
    EngineIdentity,
    MethodIdentity,
    MetricProfile,
    MetricReliability,
    MetricResult,
    MetricSelectionRule,
    MetricSensitivity,
    NormalizedDocument,
    ProfileIdentity,
    Segment,
    SelectionSummary,
    SourceIdentity,
    SourceLocation,
    WarningRecord,
)

PACKAGE_ROOT = Path(__file__).parents[1] / "src" / "hhs_nofo_metrics"
PROFILE_PATHS = tuple(sorted((PACKAGE_ROOT / "profiles").glob("*.json")))
PDF_ESTIMATE_PROFILE_PATH = (
    PACKAGE_ROOT / "profiles" / "hhs-nofo-fy27-pdf-estimate-0.5.0.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def configured_method(method_id: str) -> MethodIdentity:
    return MethodIdentity(status="configured", id=method_id, version="1.0.0")


def unavailable_passive_method() -> MethodIdentity:
    return MethodIdentity(
        status="unavailable",
        reason="No approved deterministic passive-sentence classifier is configured.",
    )


def sample_result() -> AnalysisResult:
    methods = {
        "tokenizer": configured_method("nofo-checker-word-tokenizer"),
        "sentence_segmenter": configured_method("nofo-checker-sentence-splitter"),
        "character_counter": configured_method("nofo-checker-ascii-character-counter"),
        "syllable_counter": configured_method("nofo-checker-syllable-estimator"),
        "readability_formula": configured_method("flesch-en-us"),
        "passive_classifier": unavailable_passive_method(),
    }
    selection = SelectionSummary(
        included_segment_count=2,
        excluded_segment_count=1,
        included_role_counts={"body": 2},
        excluded_role_counts={"footer": 1},
        unknown_role_policy="warn_and_include",
    )
    metrics = {
        "word_count": MetricResult(
            status="calculated",
            value=20,
            unit="words",
            method=methods["tokenizer"],
            components={"words": 20},
        ),
        "words_per_sentence": MetricResult(
            status="calculated",
            value=10.0,
            unit="words_per_sentence",
            method=methods["sentence_segmenter"],
            components={"words": 20, "sentences": 2},
        ),
        "characters_per_word": MetricResult(
            status="calculated",
            value=5.0,
            unit="characters_per_word",
            method=methods["character_counter"],
            components={"characters": 100, "words": 20},
        ),
        "flesch_reading_ease": MetricResult(
            status="calculated",
            value=60.5,
            unit="score",
            method=methods["readability_formula"],
            components={"words": 20, "sentences": 2, "syllables": 30},
        ),
        "flesch_kincaid_grade_level": MetricResult(
            status="calculated",
            value=8.2,
            unit="grade_level",
            method=methods["readability_formula"],
            components={"words": 20, "sentences": 2, "syllables": 30},
        ),
        "passive_sentence_percentage": MetricResult(
            status="not_configured",
            unit="percent",
            method=methods["passive_classifier"],
            components={},
            reason="No approved deterministic passive-sentence classifier is configured.",
        ),
    }
    return AnalysisResult(
        schema_version="1.1.0",
        analysis_id="2afdf8de-4db7-4e29-a4a8-18591290b76a",
        generated_at="2026-08-03T14:00:00Z",
        engine=EngineIdentity(name="hhs-nofo-metrics", version="0.1.0"),
        source=SourceIdentity(
            kind="pdf",
            sha256="a" * 64,
            byte_length=1234,
            production_path="unknown",
            document_id="HHS-TEST-0001",
            observed_pdf_metadata={"Producer": "Synthetic fixture"},
        ),
        adapter=AdapterIdentity(
            id="pdf",
            version="0.1.0",
            dependencies={"pdfplumber": "0.11.7", "pypdf": "6.0.0"},
        ),
        profile=ProfileIdentity(
            id="hhs-nofo-fy27",
            version="0.1.0",
            status="provisional",
            sha256="b" * 64,
        ),
        result_basis="rendered_pdf_measurement",
        methods=methods,
        coverage=CoverageSummary(
            page_count=1,
            pages_extracted=1,
            pages_with_text=1,
            extraction_error_pages=(),
            segments_total=3,
            role_counts={"body": 2, "footer": 1},
            unknown_role_count=0,
            classification_coverage=1.0,
        ),
        selection={metric_id: selection for metric_id in METRIC_IDS},
        metrics=metrics,
        warnings=(
            WarningRecord(
                code="profile_provisional",
                severity="warning",
                message="The FY27 profile is provisional.",
            ),
        ),
    )


def test_profile_schema_is_valid_and_accepts_bundled_profiles() -> None:
    schema = load_json(PACKAGE_ROOT / "schemas" / "profile-1.1.0.json")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    for path in PROFILE_PATHS:
        profile_data = load_json(path)
        validator.validate(profile_data)
        profile = MetricProfile.from_dict(profile_data)
        assert profile.to_dict() == profile_data
        assert profile.status == "provisional"
        assert profile.pipeline is not None
        assert path.name == f"{profile.profile_id}-{profile.profile_version}.json"
        assert profile.methods["passive_classifier"].status == "configured"


def test_packaged_profiles_resolve_explicit_product_pipelines() -> None:
    for path in PROFILE_PATHS:
        profile = MetricProfile.from_dict(load_json(path))
        assert profile.pipeline is not None
        assert pipeline_reference_for_profile(profile) == profile.pipeline.reference
        assert resolve_profile_pipeline(profile).default_adapter in {
            "html",
            "pdf",
            "tagged-pdf",
        }
        pipeline = resolve_profile_pipeline(profile)
        assert pipeline.source_kind in {"html", "pdf"}
        assert pipeline.estimate_kind in {"none", "tagged_pdf", "flat_pdf"}
        assert pipeline.accepts_auxiliaries is False


def test_current_distribution_contains_one_profile_per_source_behavior() -> None:
    assert {path.name for path in PROFILE_PATHS} == {
        "hhs-nofo-fy27-html-0.4.0.json",
        "hhs-nofo-fy27-pdf-estimate-0.5.0.json",
        "hhs-nofo-fy27-generic-pdf-estimate-0.4.0.json",
    }


def test_packaged_pdf_estimate_profile_is_additive_and_includes_unknowns() -> None:
    schema = load_json(PACKAGE_ROOT / "schemas" / "profile-1.1.0.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    value = load_json(PDF_ESTIMATE_PROFILE_PATH)

    validator.validate(value)
    profile = MetricProfile.from_dict(value)

    assert profile.reference == "hhs-nofo-fy27-pdf-estimate@0.5.0"
    assert profile.status == "provisional"
    assert profile.pipeline is not None
    assert profile.pipeline.reference == "hhs-tagged-pdf-estimate-analysis@0.1.0"
    assert profile.metrics["word_count"].unknown_role_policy == "warn_and_include"


def test_estimated_metric_requires_and_serializes_reliability() -> None:
    reliability = MetricReliability(
        level="moderate",
        method=MethodIdentity(
            status="configured",
            id="hhs-pdf-estimate-reliability",
            version="0.1.0",
        ),
        classification_coverage=0.98,
        unknown_segment_count=1,
        unknown_word_count=5,
        unknown_word_share=0.01,
        failed_page_count=0,
        sensitivity=MetricSensitivity(
            included_unknown_value=500,
            excluded_unknown_value=495,
            absolute_delta=5,
            relative_delta_percent=1.0,
        ),
        reason_codes=("unknown_segments_contain_word_units",),
    )
    metric = MetricResult(
        status="estimated",
        value=500,
        unit="words",
        method=configured_method("word-tokenizer"),
        components={"word_count": 500},
        reliability=reliability,
    )

    assert metric.to_dict()["reliability"]["level"] == "moderate"
    with pytest.raises(ValueError, match="estimated metrics require reliability"):
        MetricResult(
            status="estimated",
            value=500,
            unit="words",
            method=configured_method("word-tokenizer"),
        )


def test_profile_schema_requires_pipeline_only_for_version_1_1() -> None:
    value = load_json(PROFILE_PATHS[0])
    value.pop("pipeline")
    with pytest.raises(ValueError, match="requires a pipeline"):
        MetricProfile.from_dict(value)

    value = load_json(PROFILE_PATHS[0])
    value["schema_version"] = "1.0.0"
    with pytest.raises(ValueError, match="cannot declare a pipeline"):
        MetricProfile.from_dict(value)


def test_unregistered_profile_pipeline_fails_before_analysis() -> None:
    current = MetricProfile.from_dict(load_json(PROFILE_PATHS[0]))
    unsupported = replace(
        current,
        pipeline=AnalysisPipelineConfiguration(
            id="future-structured-analysis",
            version="0.1.0",
        ),
    )

    with pytest.raises(ProfileError, match="Unsupported analysis pipeline"):
        resolve_profile_pipeline(unsupported)


def test_selection_rules_reject_overlap_and_implicit_roles() -> None:
    all_roles = {
        "body",
        "heading",
        "table",
        "list",
        "cover",
        "table_of_contents",
        "instruction",
        "header",
        "footer",
        "navigation",
        "decorative",
        "unknown",
    }
    with pytest.raises(ValueError, match="both included and excluded"):
        MetricSelectionRule(
            include_roles=tuple(sorted(all_roles)),
            exclude_roles=("body",),
            unknown_role_policy="warn_and_include",
        )
    with pytest.raises(ValueError, match="every structural role"):
        MetricSelectionRule(
            include_roles=("body", "unknown"),
            exclude_roles=(),
            unknown_role_policy="warn_and_include",
        )


def test_normalized_document_preserves_text_but_report_contract_does_not() -> None:
    document = NormalizedDocument(
        source_kind="pdf",
        source_sha256="c" * 64,
        adapter_id="pdf",
        adapter_version="0.1.0",
        page_count=1,
        segments=(
            Segment(
                id="p0001-s0001",
                text="Prepublication source text.",
                location=SourceLocation(page=1, bbox=(10, 20, 200, 40)),
                reading_order=0,
                role="body",
                role_confidence="high",
                role_basis="synthetic_fixture",
                boundary_before="page",
            ),
        ),
    )
    assert document.to_dict()["segments"][0]["text"] == "Prepublication source text."
    assert "text" not in document.to_dict(include_text=False)["segments"][0]

    serialized_result = json.dumps(sample_result().to_dict())
    assert "Prepublication source text" not in serialized_result
    assert '"text"' not in serialized_result


def test_analysis_result_schema_accepts_serialized_model() -> None:
    schema = load_json(PACKAGE_ROOT / "schemas" / "analysis-result-1.1.0.json")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(
        sample_result().to_dict()
    )


def test_source_identity_rejects_nonstandard_pdf_metadata() -> None:
    with pytest.raises(
        ValueError, match="observed_pdf_metadata contains unsupported fields"
    ):
        SourceIdentity(
            kind="pdf",
            sha256="a" * 64,
            byte_length=100,
            production_path="synthetic_test",
            observed_pdf_metadata={"InternalReviewer": "Example person"},
        )

    schema = load_json(PACKAGE_ROOT / "schemas" / "analysis-result-1.1.0.json")
    invalid_result = sample_result().to_dict()
    invalid_result["source"]["observed_pdf_metadata"]["InternalReviewer"] = (
        "Example person"
    )
    errors = list(Draft202012Validator(schema).iter_errors(invalid_result))
    assert any(
        "Additional properties are not allowed" in error.message for error in errors
    )


def test_coverage_distinguishes_extracted_pages_from_pages_with_text() -> None:
    coverage = CoverageSummary(
        page_count=3,
        pages_extracted=3,
        pages_with_text=2,
        extraction_error_pages=(),
        segments_total=2,
        role_counts={"body": 2},
        unknown_role_count=0,
        classification_coverage=1.0,
    )
    assert coverage.to_dict()["pages_with_text"] == 2

    with pytest.raises(ValueError, match="must not exceed pages_extracted"):
        CoverageSummary(
            page_count=3,
            pages_extracted=2,
            pages_with_text=3,
            extraction_error_pages=(3,),
            segments_total=2,
            role_counts={"body": 2},
            unknown_role_count=0,
            classification_coverage=1.0,
        )


def test_passive_metric_cannot_claim_a_value_without_a_classifier() -> None:
    with pytest.raises(
        ValueError, match="calculated metrics require a configured method"
    ):
        MetricResult(
            status="calculated",
            value=10.0,
            unit="percent",
            method=unavailable_passive_method(),
            components={"eligible_sentences": 10, "passive_sentences": 1},
        )


def test_result_contract_requires_every_metric_and_method_slot() -> None:
    result = sample_result()
    with pytest.raises(ValueError, match="metrics must exactly match"):
        AnalysisResult(
            schema_version=result.schema_version,
            analysis_id=result.analysis_id,
            generated_at=result.generated_at,
            engine=result.engine,
            source=result.source,
            adapter=result.adapter,
            profile=result.profile,
            result_basis=result.result_basis,
            methods=result.methods,
            coverage=result.coverage,
            selection=result.selection,
            metrics={"word_count": result.metrics["word_count"]},
        )
