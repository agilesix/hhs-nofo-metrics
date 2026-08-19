"""Built-in plugins that wrap the existing extraction implementations."""

from __future__ import annotations

from typing import Mapping

from hhs_nofo_metrics.errors import AdapterContractError
from hhs_nofo_metrics.sources import MaterializedSourceBundle
from hhs_nofo_metrics.version import PACKAGE_VERSION

from .contracts import (
    ADAPTER_CONTRACT_VERSION,
    AdapterCoverage,
    AdapterDescriptor,
    AdapterEvidence,
    AdapterResult,
    JsonValue,
    SupportAssessment,
)
from .html import HtmlAdapterPlugin
from .pdf import PdfAdapter


def _distribution_version() -> str:
    return PACKAGE_VERSION


class PdfAdapterPlugin:
    descriptor = AdapterDescriptor(
        id=PdfAdapter.id,
        version=PdfAdapter.version,
        contract_version=ADAPTER_CONTRACT_VERSION,
        source_kinds=("pdf",),
        capabilities=frozenset(
            {"text", "page_geometry", "logical_roles", "reading_order", "page_mapping"}
        ),
        distribution="hhs-nofo-metrics",
        distribution_version=_distribution_version(),
    )

    def inspect_support(self, source: MaterializedSourceBundle) -> SupportAssessment:
        if source.primary.kind != "pdf":
            return SupportAssessment(
                status="unsupported",
                reason=f"Primary artifact kind is {source.primary.kind}, not pdf.",
            )
        try:
            with source.primary.path.open("rb") as stream:
                has_header = b"%PDF-" in stream.read(1024)
        except OSError as exc:
            return SupportAssessment(status="indeterminate", reason=str(exc))
        if not has_header:
            return SupportAssessment(
                status="unsupported", reason="Primary artifact has no PDF header."
            )
        return SupportAssessment(
            status="supported",
            evidence=(
                AdapterEvidence(
                    code="pdf_header",
                    value="observed",
                    confidence="high",
                ),
            ),
        )

    def extract(
        self,
        source: MaterializedSourceBundle,
        *,
        config: Mapping[str, JsonValue],
    ) -> AdapterResult:
        if config:
            raise AdapterContractError("hhs-pdf-adapter does not accept configuration")
        if source.auxiliaries:
            raise AdapterContractError(
                "hhs-pdf-adapter does not accept auxiliary artifacts"
            )
        document = PdfAdapter().extract(source.primary.path)
        error_pages = document.metadata.get("extraction_error_pages", [])
        matched_lines = int(
            document.metadata.get("line_geometry", {}).get("matched_line_count", 0)
        )
        return AdapterResult(
            document=document,
            artifacts_consumed=("primary",),
            capabilities_used=self.descriptor.capabilities,
            coverage=AdapterCoverage(
                status="partial" if error_pages else "complete",
                matched_blocks=matched_lines,
            ),
            dependencies=document.metadata.get("dependencies", {}),
        )


__all__ = ["HtmlAdapterPlugin", "PdfAdapterPlugin"]
