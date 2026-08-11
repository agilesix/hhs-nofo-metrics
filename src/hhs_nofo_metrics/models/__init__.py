"""Stable domain, profile, and result contracts."""

from .domain import (
    STRUCTURAL_ROLES,
    NormalizedDocument,
    Segment,
    SourceLocation,
)
from .profile import (
    METRIC_IDS,
    AnalysisPipelineConfiguration,
    MethodConfiguration,
    MetricProfile,
    MetricSelectionRule,
)
from .result import (
    OBSERVED_PDF_METADATA_FIELDS,
    AdapterIdentity,
    AnalysisResult,
    CoverageSummary,
    EngineIdentity,
    MethodIdentity,
    MetricReliability,
    MetricResult,
    MetricSensitivity,
    ProfileIdentity,
    SelectionSummary,
    SourceArtifactIdentity,
    SourceIdentity,
    WarningRecord,
)

__all__ = [
    "AnalysisPipelineConfiguration",
    "STRUCTURAL_ROLES",
    "METRIC_IDS",
    "OBSERVED_PDF_METADATA_FIELDS",
    "AdapterIdentity",
    "AnalysisResult",
    "CoverageSummary",
    "EngineIdentity",
    "MethodConfiguration",
    "MethodIdentity",
    "MetricProfile",
    "MetricResult",
    "MetricReliability",
    "MetricSensitivity",
    "MetricSelectionRule",
    "NormalizedDocument",
    "ProfileIdentity",
    "Segment",
    "SelectionSummary",
    "SourceIdentity",
    "SourceArtifactIdentity",
    "SourceLocation",
    "WarningRecord",
]
