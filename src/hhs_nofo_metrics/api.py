"""Small public Python API."""

from __future__ import annotations

from typing import Mapping

from hhs_nofo_metrics.adapters import (
    AdapterDescriptor,
    AdapterPlugin,
    AdapterResult,
    SupportAssessment,
    canonical_configuration_sha256,
    default_registry,
    validate_adapter_result,
)
from hhs_nofo_metrics.adapters.contracts import JsonValue
from hhs_nofo_metrics.analysis_pipelines import resolve_profile_pipeline
from hhs_nofo_metrics.errors import (
    AdapterContractError,
    AdapterExecutionError,
    NofoMetricsError,
)
from hhs_nofo_metrics.models import AnalysisResult, MetricProfile
from hhs_nofo_metrics.profile_store import (
    list_profile_references,
    load_profile_record,
)
from hhs_nofo_metrics.semantic_html_engine import analyze_semantic_document
from hhs_nofo_metrics.sources import (
    MaterializedSourceBundle,
    PdfSource,
    SourceBundle,
    materialize_source_bundle,
)


def _coerce_source_bundle(source: PdfSource | SourceBundle) -> SourceBundle:
    return source if isinstance(source, SourceBundle) else SourceBundle.from_pdf(source)


def _validate_source_support(
    plugin: AdapterPlugin,
    bundle: SourceBundle,
) -> None:
    descriptor = plugin.descriptor
    if bundle.primary.kind not in descriptor.source_kinds:
        raise AdapterContractError(
            f"Adapter {descriptor.reference} does not support primary kind "
            f"'{bundle.primary.kind}'"
        )
    unsupported_auxiliaries = {artifact.kind for artifact in bundle.auxiliaries} - set(
        descriptor.auxiliary_kinds
    )
    if unsupported_auxiliaries:
        raise AdapterContractError(
            f"Adapter {descriptor.reference} does not support auxiliary kind(s): "
            + ", ".join(sorted(unsupported_auxiliaries))
        )


def list_adapters() -> list[dict[str, object]]:
    """Return installed adapter descriptors without executing extraction."""

    return [descriptor.to_dict() for descriptor in default_registry().descriptors()]


def _inspect_support(
    plugin: AdapterPlugin,
    source: MaterializedSourceBundle,
) -> SupportAssessment:
    try:
        assessment = plugin.inspect_support(source)
    except NofoMetricsError:
        raise
    except Exception as exc:
        raise AdapterExecutionError(
            f"Adapter {plugin.descriptor.reference} support inspection failed: "
            f"{_redact_materialized_paths(str(exc), source)}"
        ) from exc
    if not isinstance(assessment, SupportAssessment):
        raise AdapterContractError(
            "adapter inspect_support() must return a SupportAssessment"
        )
    private_paths = tuple(str(artifact.path) for artifact in source.artifacts)
    public_strings = [
        *(item.code for item in assessment.evidence),
        *(item.value for item in assessment.evidence),
    ]
    if assessment.reason is not None:
        public_strings.append(assessment.reason)
    if any(
        private_path in value
        for value in public_strings
        for private_path in private_paths
    ):
        raise AdapterContractError(
            "adapter support assessment must not expose materialized artifact paths"
        )
    return assessment


def _extract(
    plugin: AdapterPlugin,
    source: MaterializedSourceBundle,
    *,
    config: Mapping[str, JsonValue],
) -> AdapterResult:
    try:
        result = plugin.extract(source, config=config)
    except NofoMetricsError:
        raise
    except Exception as exc:
        raise AdapterExecutionError(
            f"Adapter {plugin.descriptor.reference} extraction failed: "
            f"{_redact_materialized_paths(str(exc), source)}"
        ) from exc
    validate_adapter_result(plugin, source, result)
    return result


def _redact_materialized_paths(
    message: str,
    source: MaterializedSourceBundle,
) -> str:
    """Remove package-created staging paths from a public adapter error."""

    result = message
    artifact_paths = sorted(
        {str(artifact.path) for artifact in source.artifacts},
        key=len,
        reverse=True,
    )
    for path in artifact_paths:
        result = result.replace(path, "<materialized-artifact>")
    directories = sorted(
        {str(artifact.path.parent) for artifact in source.artifacts},
        key=len,
        reverse=True,
    )
    for directory in directories:
        result = result.replace(directory, "<materialized-directory>")
    return result


def list_profiles() -> list[str]:
    return list_profile_references()


def load_profile(reference: str) -> MetricProfile:
    return load_profile_record(reference)[0]


def analyze(
    source: PdfSource | SourceBundle,
    *,
    profile: str,
    adapter: str | None = None,
    production_path: str = "unknown",
    document_id: str | None = None,
    revision: str | None = None,
    adapter_config: Mapping[str, JsonValue] | None = None,
) -> AnalysisResult:
    source_bundle = _coerce_source_bundle(source)
    profile_document, profile_sha256 = load_profile_record(profile)
    pipeline = resolve_profile_pipeline(profile_document)

    selected_adapter = adapter or pipeline.default_adapter
    plugin = default_registry().resolve(selected_adapter)
    if (
        pipeline.required_adapter_id is not None
        and plugin.descriptor.id != pipeline.required_adapter_id
    ):
        raise AdapterContractError(
            f"Pipeline {pipeline.reference} requires adapter "
            f"'{pipeline.default_adapter}'"
        )
    if source_bundle.primary.kind != pipeline.source_kind:
        raise AdapterContractError(
            f"Pipeline {pipeline.reference} accepts one "
            f"{pipeline.source_kind.upper()} artifact"
        )
    if source_bundle.auxiliaries and not pipeline.accepts_auxiliaries:
        raise AdapterContractError(
            f"Pipeline {pipeline.reference} does not accept auxiliary artifacts"
        )
    _validate_source_support(plugin, source_bundle)
    config = dict(adapter_config or {})
    config_sha256 = canonical_configuration_sha256(config)
    with materialize_source_bundle(source_bundle) as materialized:
        support = _inspect_support(plugin, materialized)
        if support.status == "unsupported":
            raise AdapterContractError(
                support.reason
                or f"Adapter {plugin.descriptor.reference} does not support the source"
            )
        adapter_result = _extract(plugin, materialized, config=config)
        return analyze_semantic_document(
            adapter_result.document,
            source_bundle=materialized,
            adapter_descriptor=plugin.descriptor,
            adapter_result=adapter_result,
            adapter_configuration_sha256=config_sha256,
            support_assessment=support,
            profile=profile_document,
            profile_sha256=profile_sha256,
            production_path=production_path,
            document_id=document_id,
            revision=revision,
            estimate_kind=pipeline.estimate_kind,
        )


def inspect_adapter_support(
    source: PdfSource | SourceBundle,
    *,
    adapter: str | None = None,
) -> list[dict[str, object]]:
    """Report adapter support evidence without selecting or analyzing a source."""

    source_bundle = _coerce_source_bundle(source)
    registry = default_registry()
    plugins = (
        (registry.resolve(adapter),)
        if adapter is not None
        else tuple(registry.resolve(item.reference) for item in registry.descriptors())
    )
    results: list[dict[str, object]] = []
    with materialize_source_bundle(source_bundle) as materialized:
        for plugin in plugins:
            descriptor: AdapterDescriptor = plugin.descriptor
            if source_bundle.primary.kind not in descriptor.source_kinds:
                assessment = SupportAssessment(
                    status="unsupported",
                    reason=(
                        f"Primary artifact kind is {source_bundle.primary.kind}; "
                        f"supported kinds: {', '.join(descriptor.source_kinds)}."
                    ),
                )
            elif unsupported_auxiliaries := (
                {artifact.kind for artifact in source_bundle.auxiliaries}
                - set(descriptor.auxiliary_kinds)
            ):
                assessment = SupportAssessment(
                    status="unsupported",
                    reason=(
                        "Unsupported auxiliary kind(s): "
                        + ", ".join(sorted(unsupported_auxiliaries))
                    ),
                )
            else:
                assessment = _inspect_support(plugin, materialized)
            results.append(
                {
                    "adapter": descriptor.to_dict(),
                    "assessment": assessment.to_dict(),
                }
            )
    return results
