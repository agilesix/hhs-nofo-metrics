"""Reusable deterministic conformance checks for adapter implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hhs_nofo_metrics.errors import AdapterContractError
from hhs_nofo_metrics.sources import MaterializedSourceBundle

from .contracts import (
    AdapterPlugin,
    AdapterResult,
    JsonValue,
    canonical_configuration_sha256,
    validate_adapter_result,
)


@dataclass(frozen=True, slots=True)
class AdapterConformanceReport:
    adapter_reference: str
    configuration_sha256: str
    checks: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_reference": self.adapter_reference,
            "configuration_sha256": self.configuration_sha256,
            "checks": list(self.checks),
            "conformant": True,
        }


def _deterministic_projection(result: AdapterResult) -> dict[str, Any]:
    return {
        "document": result.document.to_dict(),
        "artifacts_consumed": list(result.artifacts_consumed),
        "capabilities_used": sorted(result.capabilities_used),
        "coverage": result.coverage.to_dict(),
        "evidence": [item.to_dict() for item in result.evidence],
        "warnings": list(result.warnings),
        "dependencies": dict(result.dependencies),
    }


def run_adapter_conformance(
    plugin: AdapterPlugin,
    source: MaterializedSourceBundle,
    *,
    config: Mapping[str, JsonValue] | None = None,
) -> AdapterConformanceReport:
    """Validate one plugin against a caller-supplied frozen source bundle."""

    configuration = dict(config or {})
    configuration_sha256 = canonical_configuration_sha256(configuration)
    descriptor = plugin.descriptor
    if source.primary.kind not in descriptor.source_kinds:
        raise AdapterContractError(
            f"Adapter {descriptor.reference} does not support primary kind "
            f"'{source.primary.kind}'"
        )
    unsupported_auxiliary_kinds = {
        artifact.kind for artifact in source.auxiliaries
    } - set(descriptor.auxiliary_kinds)
    if unsupported_auxiliary_kinds:
        raise AdapterContractError(
            f"Adapter {descriptor.reference} does not support auxiliary kind(s): "
            + ", ".join(sorted(unsupported_auxiliary_kinds))
        )

    assessment = plugin.inspect_support(source)
    if assessment.status == "unsupported":
        raise AdapterContractError(
            assessment.reason
            or f"Adapter {descriptor.reference} reported the source as unsupported"
        )

    first = plugin.extract(source, config=configuration)
    second = plugin.extract(source, config=configuration)
    validate_adapter_result(plugin, source, first)
    validate_adapter_result(plugin, source, second)
    if _deterministic_projection(first) != _deterministic_projection(second):
        raise AdapterContractError(
            f"Adapter {descriptor.reference} is not deterministic for the frozen inputs"
        )

    return AdapterConformanceReport(
        adapter_reference=descriptor.reference,
        configuration_sha256=configuration_sha256,
        checks=(
            "descriptor_valid",
            "source_contract_valid",
            "support_assessment_valid",
            "output_contract_valid",
            "deterministic_output",
            "policy_override_absent",
            "materialized_path_privacy",
        ),
    )
