"""Internal normalized-document contract shared by source adapters and the engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

STRUCTURAL_ROLES = frozenset(
    {
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
)
BOUNDARY_TYPES = frozenset({"none", "line", "paragraph", "page"})
CONFIDENCE_LEVELS = frozenset({"high", "medium", "low", "unknown"})


def _nonempty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Location of a normalized segment in its source artifact."""

    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        if self.page is not None and self.page < 1:
            raise ValueError("page must be at least 1")
        if self.bbox is not None:
            if len(self.bbox) != 4:
                raise ValueError("bbox must contain four coordinates")
            left, top, right, bottom = self.bbox
            if right < left or bottom < top:
                raise ValueError(
                    "bbox coordinates must be ordered left, top, right, bottom"
                )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.page is not None:
            result["page"] = self.page
        if self.bbox is not None:
            result["bbox"] = list(self.bbox)
        return result


@dataclass(frozen=True, slots=True)
class Segment:
    """An ordered unit of extracted text before profile selection."""

    id: str
    text: str
    location: SourceLocation
    reading_order: int
    role: str = "unknown"
    role_confidence: str = "unknown"
    role_basis: str = "adapter_default"
    boundary_before: str = "line"
    warnings: tuple[str, ...] = ()
    inclusion_override: bool | None = None

    def __post_init__(self) -> None:
        _nonempty(self.id, "segment id")
        if not isinstance(self.text, str):
            raise ValueError("segment text must be a string")
        if self.reading_order < 0:
            raise ValueError("reading_order must not be negative")
        if self.role not in STRUCTURAL_ROLES:
            raise ValueError(f"unsupported structural role: {self.role}")
        if self.role_confidence not in CONFIDENCE_LEVELS:
            raise ValueError(f"unsupported role confidence: {self.role_confidence}")
        _nonempty(self.role_basis, "role_basis")
        if self.boundary_before not in BOUNDARY_TYPES:
            raise ValueError(f"unsupported boundary type: {self.boundary_before}")

    def to_dict(self, *, include_text: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "location": self.location.to_dict(),
            "reading_order": self.reading_order,
            "role": self.role,
            "role_confidence": self.role_confidence,
            "role_basis": self.role_basis,
            "boundary_before": self.boundary_before,
            "warnings": list(self.warnings),
        }
        if include_text:
            result["text"] = self.text
        if self.inclusion_override is not None:
            result["inclusion_override"] = self.inclusion_override
        return result


@dataclass(frozen=True, slots=True)
class NormalizedDocument:
    """Adapter output. This object may contain source text and is not a report."""

    source_kind: str
    source_sha256: str
    adapter_id: str
    adapter_version: str
    segments: tuple[Segment, ...]
    page_count: int | None = None
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (
            ("source_kind", self.source_kind),
            ("source_sha256", self.source_sha256),
            ("adapter_id", self.adapter_id),
            ("adapter_version", self.adapter_version),
        ):
            _nonempty(value, name)
        if len(self.source_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.source_sha256
        ):
            raise ValueError("source_sha256 must be a lowercase SHA-256 digest")
        if self.page_count is not None and self.page_count < 0:
            raise ValueError("page_count must not be negative")
        segment_ids = [segment.id for segment in self.segments]
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError("segment ids must be unique")
        reading_order = [segment.reading_order for segment in self.segments]
        if reading_order != sorted(reading_order):
            raise ValueError("segments must be sorted by reading_order")

    def to_dict(self, *, include_text: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "source_kind": self.source_kind,
            "source_sha256": self.source_sha256,
            "adapter": {"id": self.adapter_id, "version": self.adapter_version},
            "segments": [
                segment.to_dict(include_text=include_text) for segment in self.segments
            ],
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }
        if self.page_count is not None:
            result["page_count"] = self.page_count
        return result
