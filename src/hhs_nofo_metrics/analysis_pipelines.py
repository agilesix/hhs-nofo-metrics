"""Profile-selected analysis-pipeline registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Iterable, Literal

from hhs_nofo_metrics.errors import ProfileError
from hhs_nofo_metrics.models import MetricProfile

SEMANTIC_HTML_PIPELINE_ID: Final = "hhs-semantic-html-analysis"
SEMANTIC_HTML_PIPELINE_VERSION: Final = "0.1.0"
SEMANTIC_HTML_PIPELINE_REFERENCE: Final = (
    f"{SEMANTIC_HTML_PIPELINE_ID}@{SEMANTIC_HTML_PIPELINE_VERSION}"
)
TAGGED_PDF_ESTIMATE_PIPELINE_ID: Final = "hhs-tagged-pdf-estimate-analysis"
TAGGED_PDF_ESTIMATE_PIPELINE_VERSION: Final = "0.1.0"
TAGGED_PDF_ESTIMATE_PIPELINE_REFERENCE: Final = (
    f"{TAGGED_PDF_ESTIMATE_PIPELINE_ID}@{TAGGED_PDF_ESTIMATE_PIPELINE_VERSION}"
)
GENERIC_PDF_ESTIMATE_PIPELINE_ID: Final = "hhs-generic-pdf-estimate-analysis"
GENERIC_PDF_ESTIMATE_PIPELINE_VERSION: Final = "0.1.0"
GENERIC_PDF_ESTIMATE_PIPELINE_REFERENCE: Final = (
    f"{GENERIC_PDF_ESTIMATE_PIPELINE_ID}@{GENERIC_PDF_ESTIMATE_PIPELINE_VERSION}"
)


@dataclass(frozen=True, slots=True)
class AnalysisPipelineDescriptor:
    id: str
    version: str
    default_adapter: str
    source_kind: Literal["html", "pdf"]
    required_adapter_id: str | None
    estimate_kind: Literal["none", "tagged_pdf", "flat_pdf"]
    accepts_auxiliaries: bool = False

    def __post_init__(self) -> None:
        if not self.id or not self.version or not self.default_adapter:
            raise ValueError("pipeline identity and default adapter must be non-empty")
        if self.source_kind == "html" and self.estimate_kind != "none":
            raise ValueError("HTML pipeline cannot declare a PDF estimate kind")
        if self.source_kind == "pdf" and self.estimate_kind == "none":
            raise ValueError("PDF pipeline must declare an estimate kind")

    @property
    def reference(self) -> str:
        return f"{self.id}@{self.version}"


SEMANTIC_HTML_PIPELINE = AnalysisPipelineDescriptor(
    id=SEMANTIC_HTML_PIPELINE_ID,
    version=SEMANTIC_HTML_PIPELINE_VERSION,
    default_adapter="html",
    source_kind="html",
    required_adapter_id="hhs-semantic-html-adapter",
    estimate_kind="none",
)
TAGGED_PDF_ESTIMATE_PIPELINE = AnalysisPipelineDescriptor(
    id=TAGGED_PDF_ESTIMATE_PIPELINE_ID,
    version=TAGGED_PDF_ESTIMATE_PIPELINE_VERSION,
    default_adapter="tagged-pdf",
    source_kind="pdf",
    required_adapter_id="hhs-tagged-pdf-adapter",
    estimate_kind="tagged_pdf",
)
GENERIC_PDF_ESTIMATE_PIPELINE = AnalysisPipelineDescriptor(
    id=GENERIC_PDF_ESTIMATE_PIPELINE_ID,
    version=GENERIC_PDF_ESTIMATE_PIPELINE_VERSION,
    default_adapter="pdf",
    source_kind="pdf",
    required_adapter_id=None,
    estimate_kind="flat_pdf",
)


class AnalysisPipelineRegistry:
    """Resolve exact, immutable pipeline references declared by profiles."""

    def __init__(
        self,
        descriptors: Iterable[AnalysisPipelineDescriptor] = (
            SEMANTIC_HTML_PIPELINE,
            TAGGED_PDF_ESTIMATE_PIPELINE,
            GENERIC_PDF_ESTIMATE_PIPELINE,
        ),
    ) -> None:
        self._descriptors: dict[str, AnalysisPipelineDescriptor] = {}
        for descriptor in descriptors:
            if descriptor.reference in self._descriptors:
                raise ValueError(f"duplicate analysis pipeline: {descriptor.reference}")
            self._descriptors[descriptor.reference] = descriptor

    def resolve(self, reference: str) -> AnalysisPipelineDescriptor:
        try:
            return self._descriptors[reference]
        except KeyError as exc:
            raise ProfileError(f"Unsupported analysis pipeline: {reference}") from exc


_DEFAULT_PIPELINE_REGISTRY = AnalysisPipelineRegistry()


def pipeline_reference_for_profile(profile: MetricProfile) -> str:
    """Return the profile's explicit product analysis pipeline."""

    if profile.pipeline is None:
        raise ProfileError(
            f"Profile {profile.reference} does not declare an analysis pipeline"
        )
    return profile.pipeline.reference


def resolve_profile_pipeline(profile: MetricProfile) -> AnalysisPipelineDescriptor:
    return _DEFAULT_PIPELINE_REGISTRY.resolve(pipeline_reference_for_profile(profile))
