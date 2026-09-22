"""Tagged-PDF adapter that preserves source-declared semantic block order.

The adapter intentionally requires a usable PDF structure tree. It does not
fall back to visual-line reconstruction, infer semantic roles from typography,
or claim that every tagged PDF is well structured. Untagged or unsupported
content remains ``unknown`` so profiles can fail closed.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any, Final, Mapping

import pdfplumber
from pypdf import PdfReader

from hhs_nofo_metrics.errors import AdapterContractError
from hhs_nofo_metrics.models import NormalizedDocument, Segment, SourceLocation
from hhs_nofo_metrics.sources import MaterializedSourceBundle

from .contracts import (
    ADAPTER_CONTRACT_VERSION,
    AdapterCoverage,
    AdapterDescriptor,
    AdapterEvidence,
    AdapterResult,
    JsonValue,
    SupportAssessment,
)
from .pdf import _metadata, sha256_file
from .tagged_structure import (
    dependency_versions,
    inside_panel,
    observed_words,
    right_bleed_panel_boundaries,
    tagged_content_by_page,
    visual_lines,
)

ADAPTER_ID: Final = "hhs-tagged-pdf-adapter"
ADAPTER_VERSION: Final = "0.1.5"
RESOLVER_METHOD: Final = "pdf-tagged-structure-group-resolver@0.3.5"

_ROLE_BY_GROUP_TAG: Final = {
    "P": "body",
    "H": "heading",
    "H1": "heading",
    "H2": "heading",
    "H3": "heading",
    "H4": "heading",
    "H5": "heading",
    "H6": "heading",
    "H7": "heading",
    "Lbl": "heading",
    "LBody": "list",
    "TH": "table",
    "TD": "table",
    "Caption": "heading",
    "Note": "body",
    "TOCI": "table_of_contents",
}


def _distribution_version() -> str:
    # Kept local to avoid a builtin -> tagged_pdf -> builtin import cycle.
    from hhs_nofo_metrics.version import PACKAGE_VERSION

    return PACKAGE_VERSION


def _normalized(value: str) -> str:
    return " ".join(value.split())


def _ordered_group_words(group):
    # Keep source-declared marked-content order. Within a single marked-content
    # item, font-dependent glyph tops can differ on the same baseline; sorting
    # by exact top would move bold words to the end of the line. Apply the
    # existing line tolerance only inside that item, never across tagged blocks.
    by_rank = defaultdict(list)
    for word in group:
        by_rank[word.structure_rank].append(word)
    return [
        word
        for rank in sorted(by_rank)
        for line in visual_lines(by_rank[rank])
        for word in line.words
    ]


def _bbox(words) -> tuple[float, float, float, float]:
    return (
        min(word.left for word in words),
        min(word.top for word in words),
        max(word.right for word in words),
        max(word.bottom for word in words),
    )


def _text(words) -> str:
    return " ".join(word.text for word in words).strip()


def _is_standalone_link_annotation(page, line) -> bool:
    """Recognize a complete untagged navigation line from its link annotation."""

    line_text = _normalized(line.text)
    left, top, right, bottom = _bbox(line.words)
    for annotation in page.annots:
        data = annotation.get("data") or {}
        if str(data.get("Subtype") or "").strip("/'") != "Link":
            continue
        contents = data.get("Contents")
        if isinstance(contents, bytes):
            contents = contents.decode("utf-8", errors="replace")
        if _normalized(str(contents or "")) != line_text:
            continue
        try:
            annotation_box = (
                float(annotation["x0"]),
                float(annotation["top"]),
                float(annotation["x1"]),
                float(annotation["bottom"]),
            )
        except (KeyError, TypeError, ValueError):
            continue
        annotation_left, annotation_top, annotation_right, annotation_bottom = (
            annotation_box
        )
        tolerance = 1.0
        if (
            left >= annotation_left - tolerance
            and top >= annotation_top - tolerance
            and right <= annotation_right + tolerance
            and bottom <= annotation_bottom + tolerance
        ):
            return True
    return False


def _tagged_structure(
    path: Path,
) -> tuple[dict[tuple[int, int], Any], str | None]:
    return tagged_content_by_page(path, nested_container_groups=True)


def _artifact_supported_top_navigation(words, page_number, artifact_words_by_page):
    """Require repeated source-declared artifacts, not navigation keywords.

    Builder sometimes tags the same running navigation as LBody on section
    divider pages and Artifact elsewhere. Only reclassify a complete group
    inside the top 36 points when two other pages declare matching text at
    matching positions as artifacts. Keep all uncertain groups unchanged.
    """
    if not words or any(word.bottom > 36 for word in words):
        return False
    supporting_pages = 0
    for other_page, artifacts in artifact_words_by_page.items():
        if other_page == page_number:
            continue
        if all(
            any(
                artifact.tag_path
                and artifact.tag_path[-1] == "Artifact"
                and word.text == artifact.text
                and abs(word.left - artifact.left) <= 2
                and abs(word.top - artifact.top) <= 2
                and abs(word.right - artifact.right) <= 2
                and abs(word.bottom - artifact.bottom) <= 2
                for artifact in artifacts
            )
            for word in words
        ):
            supporting_pages += 1
            if supporting_pages >= 2:
                return True
    return False


def _resolved_document(path: Path) -> NormalizedDocument:
    tagged_content, tag_error = _tagged_structure(path)
    if tag_error is not None:
        raise AdapterContractError(
            "Tagged PDF resolution could not read the PDF structure tree "
            f"({tag_error})."
        )
    if not tagged_content:
        raise AdapterContractError(
            "Tagged PDF resolution requires a non-empty PDF structure tree."
        )

    segments: list[Segment] = []
    paragraph_parts: dict[str, list[Segment]] = defaultdict(list)
    reading_order = 0
    tagged_group_count = 0
    panel_group_count = 0
    artifact_group_count = 0
    link_annotation_group_count = 0
    unknown_group_count = 0
    textless_pages: list[int] = []
    extraction_error_pages: list[int] = []
    page_count = 0
    try:
        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            page_words = {
                int(page.page_number): observed_words(page, tagged_content)
                for page in pdf.pages
            }
            artifact_words_by_page = {
                number: [
                    word
                    for word in words
                    if word.tag_path
                    and word.tag_path[-1] == "Artifact"
                    and word.bottom <= 36
                ]
                for number, words in page_words.items()
            }
            for page in pdf.pages:
                words = page_words[int(page.page_number)]
                if not words:
                    textless_pages.append(int(page.page_number))
                panels = right_bleed_panel_boundaries(page)
                grouped: dict[str, list] = defaultdict(list)
                remainder = []
                for word in words:
                    if word.structure_group_id is None:
                        remainder.append(word)
                    else:
                        grouped[word.structure_group_id].append(word)

                ordered_groups = sorted(
                    grouped.values(),
                    key=lambda values: min(
                        word.structure_rank
                        for word in values
                        if word.structure_rank is not None
                    ),
                )
                for group_index, group in enumerate(ordered_groups, start=1):
                    tagged_group_count += 1
                    ordered_words = _ordered_group_words(group)
                    group_tags = {
                        word.structure_group_tag
                        for word in ordered_words
                        if word.structure_group_tag is not None
                    }
                    group_tag = next(iter(group_tags)) if len(group_tags) == 1 else None
                    role = _ROLE_BY_GROUP_TAG.get(group_tag or "", "unknown")
                    role_basis = (
                        RESOLVER_METHOD
                        if group_tag is None
                        else f"{RESOLVER_METHOD}:{group_tag}"
                    )
                    panel_membership = {
                        panel_index
                        for panel_index, panel in enumerate(panels)
                        if any(inside_panel(word, panel) for word in ordered_words)
                    }
                    warnings = []
                    # Honor producer-declared containers, not page positions or
                    # title keywords. Nested paragraphs/headings retain their
                    # block boundaries but inherit the container's metric scope.
                    scope_roles = {
                        "cover"
                        if "HHSNofoCover" in word.tag_path
                        else "table_of_contents"
                        if "TOC" in word.tag_path or "HHSNofoContents" in word.tag_path
                        else role
                        for word in ordered_words
                    }
                    if len(scope_roles) == 1:
                        scoped_role = next(iter(scope_roles))
                        if scoped_role != role:
                            role = scoped_role
                            role_basis += ":source-declared-container"
                    else:
                        role = "unknown"
                        warnings.append("structure_group_crosses_scope_boundary")
                    if _artifact_supported_top_navigation(
                        ordered_words, int(page.page_number), artifact_words_by_page
                    ):
                        role = "navigation"
                        role_basis += ":repeated-top-artifact-support"
                    if panel_membership:
                        panel_group_count += 1
                        role_basis += ":right-bleed-panel"
                    if panel_membership and not all(
                        any(inside_panel(word, panel) for panel in panels)
                        for word in ordered_words
                    ):
                        role = "unknown"
                        warnings.append("structure_group_crosses_panel_boundary")
                    if role == "unknown":
                        unknown_group_count += 1
                        warnings.append("unsupported_structure_group_tag")
                    reading_order += 1
                    segments.append(
                        Segment(
                            id=f"p{int(page.page_number):04d}-g{group_index:04d}",
                            text=_text(ordered_words),
                            location=SourceLocation(
                                page=int(page.page_number),
                                bbox=_bbox(ordered_words),
                            ),
                            reading_order=reading_order,
                            role=role,
                            role_confidence=(
                                "unknown" if role == "unknown" else "high"
                            ),
                            role_basis=role_basis,
                            boundary_before=(
                                "page" if group_index == 1 else "paragraph"
                            ),
                            warnings=tuple(warnings),
                        )
                    )
                    if group_tag in {"P", "LBody"}:
                        paragraph_parts[ordered_words[0].structure_group_id].append(
                            segments[-1]
                        )

                for line_index, line in enumerate(visual_lines(remainder), start=1):
                    line_tags = {
                        word.tag_path[-1] for word in line.words if word.tag_path
                    }
                    is_artifact = line_tags == {"Artifact"}
                    is_standalone_link = _is_standalone_link_annotation(page, line)
                    role = (
                        "decorative"
                        if is_artifact
                        else ("navigation" if is_standalone_link else "unknown")
                    )
                    if is_artifact:
                        artifact_group_count += 1
                    elif is_standalone_link:
                        link_annotation_group_count += 1
                    else:
                        unknown_group_count += 1
                    reading_order += 1
                    segments.append(
                        Segment(
                            id=f"p{int(page.page_number):04d}-u{line_index:04d}",
                            text=line.text,
                            location=SourceLocation(
                                page=int(page.page_number),
                                bbox=_bbox(line.words),
                            ),
                            reading_order=reading_order,
                            role=role,
                            role_confidence=(
                                "high"
                                if is_artifact or is_standalone_link
                                else "unknown"
                            ),
                            role_basis=(
                                f"{RESOLVER_METHOD}:Artifact"
                                if is_artifact
                                else (
                                    f"{RESOLVER_METHOD}:LinkAnnotation"
                                    if is_standalone_link
                                    else f"{RESOLVER_METHOD}:untagged"
                                )
                            ),
                            boundary_before="paragraph",
                            warnings=(
                                ("source_declared_artifact",)
                                if is_artifact
                                else (
                                    ()
                                    if is_standalone_link
                                    else ("untagged_content_order_unresolved",)
                                )
                            ),
                        )
                    )
    except AdapterContractError:
        raise
    except Exception as exc:
        raise AdapterContractError(
            f"Tagged PDF resolution failed: {type(exc).__name__}."
        ) from exc

    # A single source-declared paragraph or list body may span multiple
    # pages. Page-local extraction must not turn its opening text into an
    # unterminated fragment. Never infer continuity from text or geometry.
    merged_locations = {}
    replacements = {}
    removed = set()
    for parts in paragraph_parts.values():
        if (
            len(parts) < 2
            or len({part.location.page for part in parts}) != len(parts)
            or any(part.role not in {"body", "list"} or part.warnings for part in parts)
            or len({part.role for part in parts}) != 1
            or len({part.role_basis for part in parts}) != 1
        ):
            continue
        first = parts[0]
        replacements[first.id] = replace(
            first,
            text=" ".join(part.text for part in parts),
            # A multi-page paragraph has no single page bounding box.
            location=SourceLocation(page=first.location.page),
            role_basis=first.role_basis
            + (
                ":cross-page-list-body"
                if first.role == "list"
                else ":cross-page-paragraph"
            ),
        )
        merged_locations[first.id] = [part.location.to_dict() for part in parts]
        removed.update(part.id for part in parts[1:])
    segments = [
        replacements.get(segment.id, segment)
        for segment in segments
        if segment.id not in removed
    ]

    metadata = {
        "cross_page_paragraph_locations": merged_locations,
        "observed_pdf_metadata": _metadata(PdfReader(path)),
        "extraction_error_pages": extraction_error_pages,
        "textless_pages": textless_pages,
        "dependencies": dependency_versions(),
        "tagged_pdf_resolution": {
            "method": RESOLVER_METHOD,
            "resolved_group_count": (
                tagged_group_count + artifact_group_count + link_annotation_group_count
            ),
            "tagged_group_count": tagged_group_count,
            "panel_group_count": panel_group_count,
            "artifact_group_count": artifact_group_count,
            "link_annotation_group_count": link_annotation_group_count,
            "unknown_group_count": unknown_group_count,
            "page_placement_basis": "pdf_structure_tree",
            "panel_semantic_role": "not_inferred",
        },
    }
    warnings = []
    if unknown_group_count:
        warnings.append("tagged_pdf_unknown_structure_groups_present")
    return NormalizedDocument(
        source_kind="pdf",
        source_sha256=sha256_file(path),
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        segments=tuple(segments),
        page_count=page_count,
        warnings=tuple(warnings),
        metadata=metadata,
    )


class TaggedPdfAdapterPlugin:
    """Explicit adapter for tagged PDFs with source-declared semantic groups."""

    descriptor = AdapterDescriptor(
        id=ADAPTER_ID,
        version=ADAPTER_VERSION,
        contract_version=ADAPTER_CONTRACT_VERSION,
        source_kinds=("pdf",),
        capabilities=frozenset(
            {
                "text",
                "page_geometry",
                "pdf_structure",
                "logical_roles",
                "reading_order",
                "page_mapping",
            }
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
        tagged_content, tag_error = _tagged_structure(source.primary.path)
        if tag_error is not None:
            return SupportAssessment(
                status="indeterminate",
                evidence=(
                    AdapterEvidence(
                        code="pdf_header", value="observed", confidence="high"
                    ),
                ),
                reason="The PDF structure tree could not be read.",
            )
        if not tagged_content:
            return SupportAssessment(
                status="unsupported",
                evidence=(
                    AdapterEvidence(
                        code="pdf_header", value="observed", confidence="high"
                    ),
                ),
                reason="The PDF has no usable tagged structure groups.",
            )
        return SupportAssessment(
            status="supported",
            evidence=(
                AdapterEvidence(code="pdf_header", value="observed", confidence="high"),
                AdapterEvidence(
                    code="tagged_structure_groups",
                    value=str(len({item.group_id for item in tagged_content.values()})),
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
            raise AdapterContractError(
                "hhs-tagged-pdf-adapter does not accept configuration"
            )
        if source.auxiliaries:
            raise AdapterContractError(
                "hhs-tagged-pdf-adapter does not accept auxiliary artifacts"
            )
        support = self.inspect_support(source)
        if support.status != "supported":
            raise AdapterContractError(
                support.reason or "Source is not supported by hhs-tagged-pdf-adapter"
            )
        document = _resolved_document(source.primary.path)
        resolution = document.metadata["tagged_pdf_resolution"]
        unknown_count = int(resolution["unknown_group_count"])
        error_pages = tuple(document.metadata.get("extraction_error_pages", ()))
        return AdapterResult(
            document=document,
            artifacts_consumed=("primary",),
            capabilities_used=self.descriptor.capabilities,
            coverage=AdapterCoverage(
                status="partial" if unknown_count or error_pages else "complete",
                matched_blocks=int(resolution["resolved_group_count"]),
                unmatched_blocks=unknown_count,
            ),
            evidence=(
                AdapterEvidence(
                    code="resolver_scope",
                    value="tagged_structure_groups",
                    confidence="high",
                ),
                AdapterEvidence(
                    code="tagged_groups_resolved",
                    value=str(resolution["tagged_group_count"]),
                    confidence="high",
                ),
                AdapterEvidence(
                    code="panel_groups_preserved",
                    value=str(resolution["panel_group_count"]),
                    confidence="medium",
                ),
                AdapterEvidence(
                    code="unknown_groups_preserved",
                    value=str(unknown_count),
                    confidence="high",
                ),
            ),
            dependencies=document.metadata.get("dependencies", {}),
        )


__all__ = [
    "ADAPTER_ID",
    "ADAPTER_VERSION",
    "RESOLVER_METHOD",
    "TaggedPdfAdapterPlugin",
]
