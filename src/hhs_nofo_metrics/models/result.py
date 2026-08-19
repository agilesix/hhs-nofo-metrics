"""Public, text-free analysis-result contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .domain import STRUCTURAL_ROLES
from .profile import METRIC_IDS, PROFILE_STATUSES, UNKNOWN_ROLE_POLICIES

METRIC_STATUSES = frozenset(
    {"calculated", "estimated", "unable_to_calculate", "not_configured"}
)
RELIABILITY_LEVELS = frozenset({"high", "moderate", "low"})
WARNING_SEVERITIES = frozenset({"info", "warning", "error"})
RESULT_BASES = frozenset({"rendered_pdf_measurement", "structured_estimate"})
OBSERVED_PDF_METADATA_FIELDS = frozenset(
    {
        "Creator",
        "Producer",
    }
)


def _required_string(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _sha256(value: str, field_name: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")


@dataclass(frozen=True, slots=True)
class EngineIdentity:
    name: str
    version: str

    def __post_init__(self) -> None:
        _required_string(self.name, "engine name")
        _required_string(self.version, "engine version")

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version}


@dataclass(frozen=True, slots=True)
class SourceArtifactIdentity:
    name: str
    kind: str
    sha256: str
    byte_length: int
    media_type: str | None = None

    def __post_init__(self) -> None:
        _required_string(self.name, "source artifact name")
        _required_string(self.kind, "source artifact kind")
        _sha256(self.sha256, "source artifact sha256")
        if self.byte_length < 0:
            raise ValueError("source artifact byte_length must not be negative")
        if self.media_type is not None:
            _required_string(self.media_type, "source artifact media_type")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self.name,
            "kind": self.kind,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
        }
        if self.media_type is not None:
            result["media_type"] = self.media_type
        return result


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    kind: str
    sha256: str
    byte_length: int
    production_path: str
    document_id: str | None = None
    revision: str | None = None
    observed_pdf_metadata: Mapping[str, str] = field(default_factory=dict)
    artifacts: tuple[SourceArtifactIdentity, ...] = ()

    def __post_init__(self) -> None:
        _required_string(self.kind, "source kind")
        _sha256(self.sha256, "source sha256")
        if self.byte_length < 0:
            raise ValueError("source byte_length must not be negative")
        _required_string(self.production_path, "production_path")
        if self.document_id is not None:
            _required_string(self.document_id, "document_id")
        if self.revision is not None:
            _required_string(self.revision, "revision")
        unsupported_metadata = (
            set(self.observed_pdf_metadata) - OBSERVED_PDF_METADATA_FIELDS
        )
        if unsupported_metadata:
            raise ValueError(
                "observed_pdf_metadata contains unsupported fields: "
                + ", ".join(sorted(unsupported_metadata))
            )
        if any(
            not isinstance(value, str) for value in self.observed_pdf_metadata.values()
        ):
            raise ValueError("observed_pdf_metadata values must be strings")
        artifact_names = [artifact.name for artifact in self.artifacts]
        if len(artifact_names) != len(set(artifact_names)):
            raise ValueError("source artifact names must be unique")
        primary = next(
            (artifact for artifact in self.artifacts if artifact.name == "primary"),
            None,
        )
        if self.artifacts and primary is None:
            raise ValueError("source artifacts must include 'primary'")
        if primary is not None and (
            primary.kind != self.kind
            or primary.sha256 != self.sha256
            or primary.byte_length != self.byte_length
        ):
            raise ValueError("primary artifact identity must match source identity")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "kind": self.kind,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
            "production_path": self.production_path,
            "observed_pdf_metadata": dict(self.observed_pdf_metadata),
        }
        if self.document_id is not None:
            result["document_id"] = self.document_id
        if self.revision is not None:
            result["revision"] = self.revision
        if self.artifacts:
            result["artifacts"] = [artifact.to_dict() for artifact in self.artifacts]
        return result


@dataclass(frozen=True, slots=True)
class AdapterIdentity:
    id: str
    version: str
    dependencies: Mapping[str, str] = field(default_factory=dict)
    contract_version: str | None = None
    distribution: str | None = None
    distribution_version: str | None = None
    configuration_sha256: str | None = None
    declared_capabilities: tuple[str, ...] = ()
    capabilities_used: tuple[str, ...] = ()
    extraction_coverage: Mapping[str, int | str] = field(default_factory=dict)
    fallback_history: tuple[str, ...] = ()
    support_evidence: tuple[Mapping[str, str], ...] = ()
    extraction_evidence: tuple[Mapping[str, str], ...] = ()

    def __post_init__(self) -> None:
        _required_string(self.id, "adapter id")
        _required_string(self.version, "adapter version")
        if any(
            not isinstance(key, str)
            or not key
            or not isinstance(value, str)
            or not value
            for key, value in self.dependencies.items()
        ):
            raise ValueError(
                "adapter dependency names and versions must be non-empty strings"
            )
        if self.contract_version is not None:
            _required_string(self.contract_version, "adapter contract_version")
        if self.distribution is not None:
            _required_string(self.distribution, "adapter distribution")
        if self.distribution_version is not None:
            _required_string(self.distribution_version, "adapter distribution_version")
        if self.configuration_sha256 is not None:
            _sha256(self.configuration_sha256, "adapter configuration_sha256")
        if len(self.declared_capabilities) != len(set(self.declared_capabilities)):
            raise ValueError("declared adapter capabilities must be unique")
        if len(self.capabilities_used) != len(set(self.capabilities_used)):
            raise ValueError("used adapter capabilities must be unique")
        if not set(self.capabilities_used).issubset(self.declared_capabilities):
            raise ValueError("used adapter capabilities must be declared")
        if len(self.fallback_history) != len(set(self.fallback_history)):
            raise ValueError("adapter fallback_history must be unique")
        if any(not value for value in self.fallback_history):
            raise ValueError("adapter fallback_history values must be non-empty")
        if self.extraction_coverage:
            required_coverage_fields = {
                "status",
                "matched_blocks",
                "unmatched_blocks",
                "ambiguous_blocks",
            }
            if set(self.extraction_coverage) != required_coverage_fields:
                raise ValueError(
                    "adapter extraction_coverage fields do not match the contract"
                )
            if self.extraction_coverage["status"] not in {
                "complete",
                "partial",
                "failed",
            }:
                raise ValueError("unsupported adapter extraction coverage status")
            for field_name in required_coverage_fields - {"status"}:
                value = self.extraction_coverage[field_name]
                if not isinstance(value, int) or value < 0:
                    raise ValueError(
                        f"adapter extraction coverage {field_name} must be a "
                        "non-negative integer"
                    )
        for evidence_name, evidence_items in (
            ("support", self.support_evidence),
            ("extraction", self.extraction_evidence),
        ):
            for evidence in evidence_items:
                if set(evidence) != {"code", "value", "confidence"}:
                    raise ValueError(
                        f"adapter {evidence_name} evidence must contain code, value, "
                        "and confidence"
                    )
                if any(
                    not isinstance(value, str) or not value
                    for value in evidence.values()
                ):
                    raise ValueError(
                        f"adapter {evidence_name} evidence values must be non-empty "
                        "strings"
                    )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "version": self.version,
            "dependencies": dict(self.dependencies),
        }
        if self.contract_version is not None:
            result["contract_version"] = self.contract_version
        if self.distribution is not None:
            result["distribution"] = self.distribution
        if self.distribution_version is not None:
            result["distribution_version"] = self.distribution_version
        if self.configuration_sha256 is not None:
            result["configuration_sha256"] = self.configuration_sha256
        if self.declared_capabilities:
            result["declared_capabilities"] = list(self.declared_capabilities)
        if self.capabilities_used:
            result["capabilities_used"] = list(self.capabilities_used)
        if self.extraction_coverage:
            result["extraction_coverage"] = dict(self.extraction_coverage)
        result["fallback_history"] = list(self.fallback_history)
        if self.support_evidence:
            result["support_evidence"] = [dict(item) for item in self.support_evidence]
        if self.extraction_evidence:
            result["extraction_evidence"] = [
                dict(item) for item in self.extraction_evidence
            ]
        return result


@dataclass(frozen=True, slots=True)
class ProfileIdentity:
    id: str
    version: str
    status: str
    sha256: str

    def __post_init__(self) -> None:
        _required_string(self.id, "profile id")
        _required_string(self.version, "profile version")
        if self.status not in PROFILE_STATUSES:
            raise ValueError(f"unsupported profile status: {self.status}")
        _sha256(self.sha256, "profile sha256")

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "version": self.version,
            "status": self.status,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class MethodIdentity:
    status: str
    id: str | None = None
    version: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"configured", "unavailable"}:
            raise ValueError(f"unsupported method identity status: {self.status}")
        if self.status == "configured":
            _required_string(self.id, "method id")
            _required_string(self.version, "method version")
            if self.reason is not None:
                raise ValueError("configured method identity must not include reason")
        else:
            _required_string(self.reason, "unavailable method reason")
            if self.id is not None or self.version is not None:
                raise ValueError(
                    "unavailable method identity must not claim id or version"
                )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"status": self.status}
        if self.id is not None:
            result["id"] = self.id
        if self.version is not None:
            result["version"] = self.version
        if self.reason is not None:
            result["reason"] = self.reason
        return result


@dataclass(frozen=True, slots=True)
class CoverageSummary:
    page_count: int
    pages_extracted: int
    pages_with_text: int
    extraction_error_pages: tuple[int, ...]
    segments_total: int
    role_counts: Mapping[str, int]
    unknown_role_count: int
    classification_coverage: float

    def __post_init__(self) -> None:
        for name, value in (
            ("page_count", self.page_count),
            ("pages_extracted", self.pages_extracted),
            ("pages_with_text", self.pages_with_text),
            ("segments_total", self.segments_total),
            ("unknown_role_count", self.unknown_role_count),
        ):
            if value < 0:
                raise ValueError(f"{name} must not be negative")
        if self.pages_extracted > self.page_count:
            raise ValueError("pages_extracted must not exceed page_count")
        if self.pages_with_text > self.pages_extracted:
            raise ValueError("pages_with_text must not exceed pages_extracted")
        if not 0 <= self.classification_coverage <= 1:
            raise ValueError("classification_coverage must be between 0 and 1")
        if set(self.role_counts) - STRUCTURAL_ROLES:
            raise ValueError("role_counts contains an unsupported role")
        if any(value < 0 for value in self.role_counts.values()):
            raise ValueError("role counts must not be negative")
        if sum(self.role_counts.values()) != self.segments_total:
            raise ValueError("role counts must sum to segments_total")
        if self.role_counts.get("unknown", 0) != self.unknown_role_count:
            raise ValueError("unknown_role_count must match role_counts.unknown")

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_count": self.page_count,
            "pages_extracted": self.pages_extracted,
            "pages_with_text": self.pages_with_text,
            "extraction_error_pages": list(self.extraction_error_pages),
            "segments_total": self.segments_total,
            "role_counts": dict(self.role_counts),
            "unknown_role_count": self.unknown_role_count,
            "classification_coverage": self.classification_coverage,
        }


@dataclass(frozen=True, slots=True)
class SelectionSummary:
    included_segment_count: int
    excluded_segment_count: int
    included_role_counts: Mapping[str, int]
    excluded_role_counts: Mapping[str, int]
    unknown_role_policy: str

    def __post_init__(self) -> None:
        if self.included_segment_count < 0 or self.excluded_segment_count < 0:
            raise ValueError("selection counts must not be negative")
        if self.unknown_role_policy not in UNKNOWN_ROLE_POLICIES:
            raise ValueError("unsupported selection unknown_role_policy")
        for counts in (self.included_role_counts, self.excluded_role_counts):
            if set(counts) - STRUCTURAL_ROLES:
                raise ValueError("selection contains an unsupported role")
            if any(value < 0 for value in counts.values()):
                raise ValueError("selection role counts must not be negative")
        if sum(self.included_role_counts.values()) != self.included_segment_count:
            raise ValueError("included role counts must sum to included_segment_count")
        if sum(self.excluded_role_counts.values()) != self.excluded_segment_count:
            raise ValueError("excluded role counts must sum to excluded_segment_count")

    def to_dict(self) -> dict[str, Any]:
        return {
            "included_segment_count": self.included_segment_count,
            "excluded_segment_count": self.excluded_segment_count,
            "included_role_counts": dict(self.included_role_counts),
            "excluded_role_counts": dict(self.excluded_role_counts),
            "unknown_role_policy": self.unknown_role_policy,
        }


@dataclass(frozen=True, slots=True)
class MetricSensitivity:
    included_unknown_value: int | float
    excluded_unknown_value: int | float | None
    absolute_delta: int | float | None
    relative_delta_percent: float | None

    def __post_init__(self) -> None:
        if self.absolute_delta is not None and self.absolute_delta < 0:
            raise ValueError("metric sensitivity absolute_delta must not be negative")
        if self.relative_delta_percent is not None and self.relative_delta_percent < 0:
            raise ValueError(
                "metric sensitivity relative_delta_percent must not be negative"
            )

    def to_dict(self) -> dict[str, int | float | None]:
        return {
            "included_unknown_value": self.included_unknown_value,
            "excluded_unknown_value": self.excluded_unknown_value,
            "absolute_delta": self.absolute_delta,
            "relative_delta_percent": self.relative_delta_percent,
        }


@dataclass(frozen=True, slots=True)
class MetricReliability:
    level: str
    method: MethodIdentity
    classification_coverage: float
    unknown_segment_count: int
    unknown_word_count: int
    unknown_word_share: float
    failed_page_count: int
    sensitivity: MetricSensitivity
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.level not in RELIABILITY_LEVELS:
            raise ValueError(f"unsupported reliability level: {self.level}")
        if self.method.status != "configured":
            raise ValueError("metric reliability requires a configured method")
        for field_name in ("classification_coverage", "unknown_word_share"):
            value = getattr(self, field_name)
            if not 0 <= value <= 1:
                raise ValueError(f"{field_name} must be between 0 and 1")
        for field_name in (
            "unknown_segment_count",
            "unknown_word_count",
            "failed_page_count",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must not be negative")
        if not self.reason_codes:
            raise ValueError("metric reliability requires at least one reason code")
        if len(self.reason_codes) != len(set(self.reason_codes)):
            raise ValueError("metric reliability reason codes must be unique")
        if any(not value for value in self.reason_codes):
            raise ValueError("metric reliability reason codes must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "method": self.method.to_dict(),
            "classification_coverage": self.classification_coverage,
            "unknown_segment_count": self.unknown_segment_count,
            "unknown_word_count": self.unknown_word_count,
            "unknown_word_share": self.unknown_word_share,
            "failed_page_count": self.failed_page_count,
            "sensitivity": self.sensitivity.to_dict(),
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True, slots=True)
class MetricResult:
    status: str
    unit: str
    method: MethodIdentity
    value: int | float | None = None
    components: Mapping[str, int | float] = field(default_factory=dict)
    reason: str | None = None
    reliability: MetricReliability | None = None

    def __post_init__(self) -> None:
        if self.status not in METRIC_STATUSES:
            raise ValueError(f"unsupported metric status: {self.status}")
        _required_string(self.unit, "metric unit")
        if self.status in {"calculated", "estimated"}:
            if self.value is None:
                raise ValueError(f"{self.status} metrics require a value")
            if self.reason is not None:
                raise ValueError(
                    f"{self.status} metrics must not include an unable reason"
                )
            if self.method.status != "configured":
                raise ValueError(f"{self.status} metrics require a configured method")
            if self.status == "estimated" and self.reliability is None:
                raise ValueError("estimated metrics require reliability evidence")
            if self.status == "calculated" and self.reliability is not None:
                raise ValueError("calculated metrics must not include reliability")
        else:
            if self.value is not None:
                raise ValueError("uncalculated metrics must not include a value")
            _required_string(self.reason, "uncalculated metric reason")
            if self.reliability is not None:
                raise ValueError("uncalculated metrics must not include reliability")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": self.status,
            "unit": self.unit,
            "method": self.method.to_dict(),
            "components": dict(self.components),
        }
        if self.value is not None:
            result["value"] = self.value
        if self.reason is not None:
            result["reason"] = self.reason
        if self.reliability is not None:
            result["reliability"] = self.reliability.to_dict()
        return result


@dataclass(frozen=True, slots=True)
class WarningRecord:
    code: str
    severity: str
    message: str
    pages: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        _required_string(self.code, "warning code")
        if self.severity not in WARNING_SEVERITIES:
            raise ValueError(f"unsupported warning severity: {self.severity}")
        _required_string(self.message, "warning message")
        if any(page < 1 for page in self.pages):
            raise ValueError("warning pages must be at least 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "pages": list(self.pages),
        }


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    schema_version: str
    analysis_id: str
    generated_at: str
    engine: EngineIdentity
    source: SourceIdentity
    adapter: AdapterIdentity
    profile: ProfileIdentity
    result_basis: str
    methods: Mapping[str, MethodIdentity]
    coverage: CoverageSummary
    selection: Mapping[str, SelectionSummary]
    metrics: Mapping[str, MetricResult]
    warnings: tuple[WarningRecord, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (
            ("schema_version", self.schema_version),
            ("analysis_id", self.analysis_id),
            ("generated_at", self.generated_at),
        ):
            _required_string(value, name)
        if self.result_basis not in RESULT_BASES:
            raise ValueError(f"unsupported result_basis: {self.result_basis}")
        if set(self.metrics) != set(METRIC_IDS):
            raise ValueError("analysis metrics must exactly match supported metric ids")
        if set(self.selection) != set(METRIC_IDS):
            raise ValueError(
                "analysis selection must exactly match supported metric ids"
            )
        required_methods = {
            "tokenizer",
            "sentence_segmenter",
            "character_counter",
            "syllable_counter",
            "readability_formula",
            "passive_classifier",
        }
        if set(self.methods) != required_methods:
            raise ValueError(
                "analysis methods must exactly match supported method slots"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "analysis_id": self.analysis_id,
            "generated_at": self.generated_at,
            "engine": self.engine.to_dict(),
            "source": self.source.to_dict(),
            "adapter": self.adapter.to_dict(),
            "profile": self.profile.to_dict(),
            "result_basis": self.result_basis,
            "methods": {
                slot: identity.to_dict() for slot, identity in self.methods.items()
            },
            "coverage": self.coverage.to_dict(),
            "selection": {
                metric_id: summary.to_dict()
                for metric_id, summary in self.selection.items()
            },
            "metrics": {
                metric_id: result.to_dict()
                for metric_id, result in self.metrics.items()
            },
            "warnings": [warning.to_dict() for warning in self.warnings],
        }
