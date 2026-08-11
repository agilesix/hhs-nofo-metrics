"""Source adapters."""

from .conformance import AdapterConformanceReport, run_adapter_conformance
from .contracts import (
    ADAPTER_CAPABILITIES,
    ADAPTER_CONTRACT_VERSION,
    AdapterCoverage,
    AdapterDescriptor,
    AdapterEvidence,
    AdapterPlugin,
    AdapterResult,
    SupportAssessment,
    canonical_configuration_sha256,
    validate_adapter_result,
)
from .pdf import ADAPTER_ID, ADAPTER_VERSION, PdfAdapter
from .registry import AdapterRegistry, create_default_registry, default_registry
from .tagged_pdf import TaggedPdfAdapterPlugin

__all__ = [
    "ADAPTER_ID",
    "ADAPTER_VERSION",
    "ADAPTER_CAPABILITIES",
    "ADAPTER_CONTRACT_VERSION",
    "AdapterCoverage",
    "AdapterConformanceReport",
    "AdapterDescriptor",
    "AdapterEvidence",
    "AdapterPlugin",
    "AdapterRegistry",
    "AdapterResult",
    "PdfAdapter",
    "SupportAssessment",
    "TaggedPdfAdapterPlugin",
    "canonical_configuration_sha256",
    "create_default_registry",
    "default_registry",
    "run_adapter_conformance",
    "validate_adapter_result",
]
