"""Versioned metric-profile contract and validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from .domain import STRUCTURAL_ROLES

METRIC_IDS = (
    "word_count",
    "words_per_sentence",
    "characters_per_word",
    "flesch_reading_ease",
    "flesch_kincaid_grade_level",
    "passive_sentence_percentage",
)
PROFILE_STATUSES = frozenset({"provisional", "approved", "retired"})
UNKNOWN_ROLE_POLICIES = frozenset(
    {"warn_and_include", "warn_and_exclude", "unable_to_calculate"}
)
METHOD_STATUSES = frozenset({"configured", "unavailable"})
_PIPELINE_ID_RE = re.compile(r"^[a-z0-9]+(?:[a-z0-9._-]*[a-z0-9])?$")
_SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def _required_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class MetricSelectionRule:
    include_roles: tuple[str, ...]
    exclude_roles: tuple[str, ...]
    unknown_role_policy: str

    def __post_init__(self) -> None:
        included = set(self.include_roles)
        excluded = set(self.exclude_roles)
        unsupported = (included | excluded) - STRUCTURAL_ROLES
        if unsupported:
            raise ValueError(f"unsupported structural roles: {sorted(unsupported)}")
        overlap = included & excluded
        if overlap:
            raise ValueError(
                f"roles cannot be both included and excluded: {sorted(overlap)}"
            )
        missing = STRUCTURAL_ROLES - included - excluded
        if missing:
            raise ValueError(
                f"every structural role must be classified: {sorted(missing)}"
            )
        if self.unknown_role_policy not in UNKNOWN_ROLE_POLICIES:
            raise ValueError(
                f"unsupported unknown_role_policy: {self.unknown_role_policy}"
            )
        if self.unknown_role_policy == "warn_and_include" and "unknown" not in included:
            raise ValueError("warn_and_include requires unknown in include_roles")
        if (
            self.unknown_role_policy in {"warn_and_exclude", "unable_to_calculate"}
            and "unknown" not in excluded
        ):
            raise ValueError(
                f"{self.unknown_role_policy} requires unknown in exclude_roles"
            )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MetricSelectionRule":
        return cls(
            include_roles=tuple(value["include_roles"]),
            exclude_roles=tuple(value["exclude_roles"]),
            unknown_role_policy=value["unknown_role_policy"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "include_roles": list(self.include_roles),
            "exclude_roles": list(self.exclude_roles),
            "unknown_role_policy": self.unknown_role_policy,
        }


@dataclass(frozen=True, slots=True)
class MethodConfiguration:
    status: str
    id: str | None = None
    version: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in METHOD_STATUSES:
            raise ValueError(f"unsupported method status: {self.status}")
        if self.status == "configured":
            _required_string(self.id, "configured method id")
            _required_string(self.version, "configured method version")
            if self.reason is not None:
                raise ValueError(
                    "configured methods must not include an unavailable reason"
                )
        else:
            _required_string(self.reason, "unavailable method reason")
            if self.id is not None or self.version is not None:
                raise ValueError("unavailable methods must not claim an id or version")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MethodConfiguration":
        return cls(
            status=value["status"],
            id=value.get("id"),
            version=value.get("version"),
            reason=value.get("reason"),
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
class AnalysisPipelineConfiguration:
    """Immutable analysis-pipeline identity selected by a profile."""

    id: str
    version: str

    def __post_init__(self) -> None:
        _required_string(self.id, "pipeline id")
        _required_string(self.version, "pipeline version")
        if _PIPELINE_ID_RE.fullmatch(self.id) is None:
            raise ValueError("pipeline id contains unsupported characters")
        if _SEMVER_RE.fullmatch(self.version) is None:
            raise ValueError("pipeline version must use semantic versioning")

    @property
    def reference(self) -> str:
        return f"{self.id}@{self.version}"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AnalysisPipelineConfiguration":
        return cls(id=value["id"], version=value["version"])

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "version": self.version}


@dataclass(frozen=True, slots=True)
class MetricProfile:
    schema_version: str
    profile_id: str
    profile_version: str
    status: str
    description: str
    metrics: Mapping[str, MetricSelectionRule]
    methods: Mapping[str, MethodConfiguration]
    pipeline: AnalysisPipelineConfiguration | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("schema_version", self.schema_version),
            ("profile_id", self.profile_id),
            ("profile_version", self.profile_version),
            ("description", self.description),
        ):
            _required_string(value, name)
        if self.status not in PROFILE_STATUSES:
            raise ValueError(f"unsupported profile status: {self.status}")
        if self.schema_version == "1.0.0" and self.pipeline is not None:
            raise ValueError("profile schema 1.0.0 cannot declare a pipeline")
        if self.schema_version == "1.1.0" and self.pipeline is None:
            raise ValueError("profile schema 1.1.0 requires a pipeline")
        if self.schema_version not in {"1.0.0", "1.1.0"}:
            raise ValueError(f"unsupported profile schema: {self.schema_version}")
        metric_ids = set(self.metrics)
        if metric_ids != set(METRIC_IDS):
            raise ValueError(
                "profile metrics must exactly match the supported metric ids; "
                f"missing={sorted(set(METRIC_IDS) - metric_ids)}, "
                f"extra={sorted(metric_ids - set(METRIC_IDS))}"
            )
        required_methods = {
            "tokenizer",
            "sentence_segmenter",
            "character_counter",
            "syllable_counter",
            "readability_formula",
            "passive_classifier",
        }
        method_ids = set(self.methods)
        if method_ids != required_methods:
            raise ValueError(
                "profile methods must exactly match the supported method slots; "
                f"missing={sorted(required_methods - method_ids)}, "
                f"extra={sorted(method_ids - required_methods)}"
            )

    @property
    def reference(self) -> str:
        return f"{self.profile_id}@{self.profile_version}"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MetricProfile":
        return cls(
            schema_version=value["schema_version"],
            profile_id=value["profile_id"],
            profile_version=value["profile_version"],
            status=value["status"],
            description=value["description"],
            metrics={
                metric_id: MetricSelectionRule.from_dict(rule)
                for metric_id, rule in value["metrics"].items()
            },
            methods={
                method_slot: MethodConfiguration.from_dict(configuration)
                for method_slot, configuration in value["methods"].items()
            },
            pipeline=(
                AnalysisPipelineConfiguration.from_dict(value["pipeline"])
                if "pipeline" in value
                else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "status": self.status,
            "description": self.description,
            "metrics": {
                metric_id: rule.to_dict() for metric_id, rule in self.metrics.items()
            },
            "methods": {
                method_slot: configuration.to_dict()
                for method_slot, configuration in self.methods.items()
            },
        }
        if self.pipeline is not None:
            result["pipeline"] = self.pipeline.to_dict()
        return result
