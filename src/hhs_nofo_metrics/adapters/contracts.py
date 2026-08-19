"""Versioned extraction-adapter contract owned by the core package."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping, Protocol, TypeAlias

from hhs_nofo_metrics.errors import AdapterContractError
from hhs_nofo_metrics.models import NormalizedDocument, Segment
from hhs_nofo_metrics.sources import MaterializedSourceBundle

ADAPTER_CONTRACT_VERSION = "1.0.0"
ADAPTER_COVERAGE_STATUSES = frozenset({"complete", "partial", "failed"})
SUPPORT_STATUSES = frozenset({"supported", "unsupported", "indeterminate"})
EVIDENCE_CONFIDENCE_LEVELS = frozenset({"high", "medium", "low", "unknown"})
ADAPTER_CAPABILITIES = frozenset(
    {
        "text",
        "page_geometry",
        "pdf_structure",
        "logical_roles",
        "reading_order",
        "page_mapping",
        "sidecar_alignment",
    }
)
_SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
_ADAPTER_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


def _required_string(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _validate_json_value(value: object, *, path: str) -> None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, path=f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise AdapterContractError(
                    f"Adapter configuration key at {path} must be a string"
                )
            _validate_json_value(item, path=f"{path}.{key}")
        return
    raise AdapterContractError(
        f"Adapter configuration value at {path} is not a JSON value"
    )


def canonical_configuration_sha256(config: Mapping[str, JsonValue]) -> str:
    _validate_json_value(dict(config), path="config")
    try:
        payload = json.dumps(
            config,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AdapterContractError(
            f"Adapter configuration must contain only JSON values: {exc}"
        ) from exc
    return sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class AdapterDescriptor:
    id: str
    version: str
    contract_version: str = ADAPTER_CONTRACT_VERSION
    source_kinds: tuple[str, ...] = ("pdf",)
    auxiliary_kinds: tuple[str, ...] = ()
    capabilities: frozenset[str] = frozenset()
    distribution: str | None = None
    distribution_version: str | None = None

    def __post_init__(self) -> None:
        _required_string(self.id, "adapter id")
        _required_string(self.version, "adapter version")
        _required_string(self.contract_version, "adapter contract version")
        if not _ADAPTER_ID_RE.fullmatch(self.id):
            raise ValueError("adapter id contains unsupported characters")
        if not _SEMVER_RE.fullmatch(self.version):
            raise ValueError("adapter version must use semantic versioning")
        if self.contract_version != ADAPTER_CONTRACT_VERSION:
            raise ValueError(
                "unsupported adapter contract version: " + self.contract_version
            )
        if not self.source_kinds or any(
            not isinstance(value, str) or not value.strip()
            for value in self.source_kinds
        ):
            raise ValueError("adapter source_kinds must contain non-empty values")
        if len(self.source_kinds) != len(set(self.source_kinds)):
            raise ValueError("adapter source_kinds must be unique")
        if any(
            not isinstance(value, str) or not value.strip()
            for value in self.auxiliary_kinds
        ):
            raise ValueError("adapter auxiliary_kinds must contain non-empty values")
        if len(self.auxiliary_kinds) != len(set(self.auxiliary_kinds)):
            raise ValueError("adapter auxiliary_kinds must be unique")
        if any(not isinstance(value, str) for value in self.capabilities):
            raise ValueError("adapter capabilities must be strings")
        unsupported = self.capabilities - ADAPTER_CAPABILITIES
        if unsupported:
            raise ValueError(
                "unsupported adapter capabilities: " + ", ".join(sorted(unsupported))
            )
        if self.distribution is not None:
            _required_string(self.distribution, "adapter distribution")
        if self.distribution_version is not None:
            _required_string(self.distribution_version, "adapter distribution_version")

    @property
    def reference(self) -> str:
        return f"{self.id}@{self.version}"

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "version": self.version,
            "reference": self.reference,
            "contract_version": self.contract_version,
            "source_kinds": list(self.source_kinds),
            "auxiliary_kinds": list(self.auxiliary_kinds),
            "capabilities": sorted(self.capabilities),
        }
        if self.distribution is not None:
            result["distribution"] = self.distribution
        if self.distribution_version is not None:
            result["distribution_version"] = self.distribution_version
        return result


@dataclass(frozen=True, slots=True)
class AdapterEvidence:
    code: str
    value: str
    confidence: str = "unknown"

    def __post_init__(self) -> None:
        _required_string(self.code, "adapter evidence code")
        _required_string(self.value, "adapter evidence value")
        if self.confidence not in EVIDENCE_CONFIDENCE_LEVELS:
            raise ValueError(f"unsupported evidence confidence: {self.confidence}")

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "value": self.value,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class SupportAssessment:
    status: str
    evidence: tuple[AdapterEvidence, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in SUPPORT_STATUSES:
            raise ValueError(f"unsupported support status: {self.status}")
        if self.reason is not None:
            _required_string(self.reason, "support assessment reason")
        if any(not isinstance(item, AdapterEvidence) for item in self.evidence):
            raise ValueError("support evidence must contain AdapterEvidence values")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": self.status,
            "evidence": [item.to_dict() for item in self.evidence],
        }
        if self.reason is not None:
            result["reason"] = self.reason
        return result


@dataclass(frozen=True, slots=True)
class AdapterCoverage:
    status: str
    matched_blocks: int = 0
    unmatched_blocks: int = 0
    ambiguous_blocks: int = 0

    def __post_init__(self) -> None:
        if self.status not in ADAPTER_COVERAGE_STATUSES:
            raise ValueError(f"unsupported adapter coverage status: {self.status}")
        for name, value in (
            ("matched_blocks", self.matched_blocks),
            ("unmatched_blocks", self.unmatched_blocks),
            ("ambiguous_blocks", self.ambiguous_blocks),
        ):
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")

    def to_dict(self) -> dict[str, int | str]:
        return {
            "status": self.status,
            "matched_blocks": self.matched_blocks,
            "unmatched_blocks": self.unmatched_blocks,
            "ambiguous_blocks": self.ambiguous_blocks,
        }


@dataclass(frozen=True, slots=True)
class AdapterResult:
    document: NormalizedDocument
    artifacts_consumed: tuple[str, ...]
    capabilities_used: frozenset[str]
    coverage: AdapterCoverage
    evidence: tuple[AdapterEvidence, ...] = ()
    warnings: tuple[str, ...] = ()
    dependencies: Mapping[str, str] = field(default_factory=dict)


class AdapterPlugin(Protocol):
    descriptor: AdapterDescriptor

    def inspect_support(
        self, source: MaterializedSourceBundle
    ) -> SupportAssessment: ...

    def extract(
        self,
        source: MaterializedSourceBundle,
        *,
        config: Mapping[str, JsonValue],
    ) -> AdapterResult: ...


def validate_adapter_result(
    plugin: AdapterPlugin,
    source: MaterializedSourceBundle,
    result: AdapterResult,
) -> None:
    if not isinstance(result, AdapterResult):
        raise AdapterContractError("adapter extract() must return an AdapterResult")
    if not isinstance(result.document, NormalizedDocument):
        raise AdapterContractError(
            "adapter result document must be a NormalizedDocument"
        )
    if not isinstance(result.document.segments, tuple):
        raise AdapterContractError("normalized document segments must be a tuple")
    if not all(isinstance(item, Segment) for item in result.document.segments):
        raise AdapterContractError(
            "normalized document segments must contain Segment values"
        )
    if not isinstance(result.document.warnings, tuple):
        raise AdapterContractError("normalized document warnings must be a tuple")
    if not isinstance(result.document.metadata, Mapping):
        raise AdapterContractError("normalized document metadata must be a mapping")
    if not isinstance(result.coverage, AdapterCoverage):
        raise AdapterContractError("adapter result coverage must be an AdapterCoverage")
    if not isinstance(result.artifacts_consumed, tuple):
        raise AdapterContractError("adapter artifacts_consumed must be a tuple")
    if any(
        not isinstance(value, str) or not value for value in result.artifacts_consumed
    ):
        raise AdapterContractError(
            "adapter artifacts_consumed must contain non-empty strings"
        )
    if not isinstance(result.capabilities_used, frozenset) or any(
        not isinstance(value, str) for value in result.capabilities_used
    ):
        raise AdapterContractError(
            "adapter capabilities_used must be a frozenset of strings"
        )
    if not isinstance(result.dependencies, Mapping):
        raise AdapterContractError("adapter dependencies must be a mapping")
    if not isinstance(result.warnings, tuple):
        raise AdapterContractError("adapter warnings must be a tuple")
    if not isinstance(result.evidence, tuple):
        raise AdapterContractError("adapter evidence must be a tuple")
    descriptor = plugin.descriptor
    artifact_names = {artifact.name for artifact in source.artifacts}
    if not result.artifacts_consumed:
        raise AdapterContractError("adapter must report at least one consumed artifact")
    if len(result.artifacts_consumed) != len(set(result.artifacts_consumed)):
        raise AdapterContractError("adapter artifacts_consumed must be unique")
    missing = set(result.artifacts_consumed) - artifact_names
    if missing:
        raise AdapterContractError(
            "adapter reported unknown consumed artifacts: " + ", ".join(sorted(missing))
        )
    if "primary" not in result.artifacts_consumed:
        raise AdapterContractError("adapter must consume the primary artifact")
    if result.document.source_sha256 != source.primary.sha256:
        raise AdapterContractError(
            "normalized document hash does not match the primary artifact"
        )
    if result.document.source_kind != source.primary.kind:
        raise AdapterContractError(
            "normalized document source_kind does not match the primary artifact"
        )
    if result.document.adapter_id != descriptor.id:
        raise AdapterContractError(
            "normalized document adapter_id does not match the descriptor"
        )
    if result.document.adapter_version != descriptor.version:
        raise AdapterContractError(
            "normalized document adapter_version does not match the descriptor"
        )
    unsupported = result.capabilities_used - descriptor.capabilities
    if unsupported:
        raise AdapterContractError(
            "adapter used undeclared capabilities: " + ", ".join(sorted(unsupported))
        )
    if any(
        segment.inclusion_override is not None for segment in result.document.segments
    ):
        raise AdapterContractError("adapters may not set Segment.inclusion_override")
    if result.coverage.status == "failed":
        raise AdapterContractError("failed adapter coverage cannot be analyzed")
    if any(
        not isinstance(key, str) or not key or not isinstance(value, str) or not value
        for key, value in result.dependencies.items()
    ):
        raise AdapterContractError(
            "adapter dependency names and versions must be non-empty strings"
        )
    if any(not isinstance(value, str) or not value for value in result.warnings):
        raise AdapterContractError("adapter warnings must be non-empty strings")
    if any(
        not isinstance(value, str) or not value for value in result.document.warnings
    ):
        raise AdapterContractError(
            "normalized document warnings must be non-empty strings"
        )
    if any(not isinstance(item, AdapterEvidence) for item in result.evidence):
        raise AdapterContractError(
            "adapter evidence must contain AdapterEvidence values"
        )
    private_paths = tuple(str(artifact.path) for artifact in source.artifacts)
    public_strings = [
        *result.warnings,
        *result.document.warnings,
        *result.dependencies.keys(),
        *result.dependencies.values(),
        *(item.code for item in result.evidence),
        *(item.value for item in result.evidence),
    ]
    if any(
        private_path in value
        for value in public_strings
        for private_path in private_paths
    ):
        raise AdapterContractError(
            "adapter output must not expose materialized artifact paths"
        )
