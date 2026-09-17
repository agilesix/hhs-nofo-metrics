from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfWriter

from hhs_nofo_metrics import AdapterContractError, InputError
from hhs_nofo_metrics.adapters.tagged_pdf import (
    TaggedPdfAdapterPlugin,
    _artifact_supported_top_navigation,
    _is_standalone_link_annotation,
)
from hhs_nofo_metrics.adapters.tagged_structure import (
    ObservedWord,
    PanelBoundary,
    TaggedContent,
    dependency_versions,
    inside_panel,
    observed_words,
    right_bleed_panel_boundaries,
    tagged_content_by_page,
    visual_lines,
)
from hhs_nofo_metrics.sources import (
    MaterializedArtifact,
    MaterializedSourceBundle,
    SourceArtifact,
    SourceBundle,
    materialize_source_bundle,
)


def word(
    text: str,
    *,
    left: float,
    top: float,
    native_index: int,
    tag_path: tuple[str, ...] = (),
) -> ObservedWord:
    return ObservedWord(
        text=text,
        left=left,
        top=top,
        right=left + 20,
        bottom=top + 10,
        font_name="Helvetica",
        font_size=10,
        native_index=native_index,
        marked_content_id=None,
        tag_path=tag_path,
        structure_rank=None,
        structure_group_id=None,
        structure_group_tag=None,
    )


def write_blank_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with path.open("wb") as stream:
        writer.write(stream)


def test_top_navigation_requires_two_other_artifact_pages_and_full_geometry_match():
    nav = word("Review", left=20, top=10, native_index=0)
    artifact = word("Review", left=20, top=11, native_index=0, tag_path=("Artifact",))
    assert _artifact_supported_top_navigation([nav], 1, {2: [artifact], 3: [artifact]})
    assert not _artifact_supported_top_navigation(
        [nav], 1, {1: [artifact], 2: [artifact]}
    )
    assert not _artifact_supported_top_navigation([nav], 1, {2: [artifact]})
    body = word("Review", left=20, top=100, native_index=0)
    assert not _artifact_supported_top_navigation(
        [body], 1, {2: [artifact], 3: [artifact]}
    )
    unmatched = word("Instructions", left=50, top=10, native_index=1)
    assert not _artifact_supported_top_navigation(
        [nav, unmatched], 1, {2: [artifact], 3: [artifact]}
    )
    moved = word("Review", left=100, top=10, native_index=0)
    assert not _artifact_supported_top_navigation(
        [moved], 1, {2: [artifact], 3: [artifact]}
    )
    assert not _artifact_supported_top_navigation([nav], 1, {2: [nav], 3: [nav]})
    boundary = word("Review", left=20, top=26, native_index=0)
    boundary_artifact = word(
        "Review", left=20, top=26, native_index=0, tag_path=("Artifact",)
    )
    assert _artifact_supported_top_navigation(
        [boundary], 1, {2: [boundary_artifact], 3: [boundary_artifact]}
    )
    outside = word("Review", left=20, top=26.1, native_index=0)
    assert not _artifact_supported_top_navigation(
        [outside], 1, {2: [boundary_artifact], 3: [boundary_artifact]}
    )


def test_observed_words_preserves_tagged_semantics_and_bounded_optional_values() -> (
    None
):
    page = SimpleNamespace(
        page_number=2,
        extract_words=lambda **kwargs: [
            {"text": "   "},
            {
                "text": "Tagged",
                "x0": "10",
                "top": "20",
                "x1": "40",
                "bottom": "30",
                "fontname": " Helvetica ",
                "size": "10.5",
                "mcid": "4",
                "tag": "/P",
            },
            {
                "text": "Artifact",
                "x0": 50,
                "top": 20,
                "x1": 90,
                "bottom": 30,
                "size": "invalid",
                "mcid": "invalid",
                "tag": "/Artifact",
            },
        ],
    )
    tagged = TaggedContent(
        rank=7,
        tag_path=("Document", "P"),
        group_id="group-1",
        group_tag="P",
    )

    values = observed_words(page, {(2, 4): tagged})

    assert [item.text for item in values] == ["Tagged", "Artifact"]
    assert values[0].font_name == "Helvetica"
    assert values[0].font_size == 10.5
    assert values[0].marked_content_id == 4
    assert values[0].tag_path == ("Document", "P")
    assert values[0].structure_rank == 7
    assert values[0].structure_group_id == "group-1"
    assert values[1].font_size is None
    assert values[1].marked_content_id is None
    assert values[1].tag_path == ("Artifact",)


def test_observed_words_translates_extraction_and_geometry_failures() -> None:
    broken_extraction = SimpleNamespace(
        page_number=1,
        extract_words=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    with pytest.raises(InputError, match="Unable to extract tagged PDF words: boom"):
        observed_words(broken_extraction, {})

    invalid_geometry = SimpleNamespace(
        page_number=1,
        extract_words=lambda **kwargs: [{"text": "word", "x0": "bad"}],
    )
    with pytest.raises(InputError, match="missing valid geometry"):
        observed_words(invalid_geometry, {})


def test_visual_lines_preserve_reading_order_and_geometry_properties() -> None:
    values = (
        word("second", left=40, top=10, native_index=1),
        word("first", left=10, top=11, native_index=0),
        word("next", left=10, top=30, native_index=2),
    )

    lines = visual_lines(values)

    assert [line.text for line in lines] == ["first second", "next"]
    assert lines[0].top == 10
    assert lines[0].bottom == 21


def test_right_bleed_panels_are_bounded_sorted_and_deduplicated() -> None:
    page = SimpleNamespace(
        width=1000,
        rects=[
            {"fill": False, "non_stroking_color": 1},
            {"fill": True, "non_stroking_color": 1, "x0": "bad"},
            {
                "fill": True,
                "non_stroking_color": 1,
                "x0": 850,
                "top": 100,
                "x1": 1000,
                "bottom": 300,
            },
            {
                "fill": True,
                "non_stroking_color": 1,
                "x0": 852,
                "top": 102,
                "x1": 998,
                "bottom": 298,
            },
            {
                "fill": True,
                "non_stroking_color": 1,
                "x0": 950,
                "top": 10,
                "x1": 1000,
                "bottom": 20,
            },
        ],
        curves=[
            {
                "fill": True,
                "non_stroking_color": 1,
                "x0": 800,
                "top": 350,
                "x1": 1000,
                "bottom": 500,
            }
        ],
    )

    panels = right_bleed_panel_boundaries(page)

    assert panels == (
        PanelBoundary(left=850, top=100, right=1000, bottom=300),
        PanelBoundary(left=800, top=350, right=1000, bottom=500),
    )
    assert inside_panel(word("inside", left=900, top=150, native_index=0), panels[0])
    assert not inside_panel(
        word("outside", left=100, top=150, native_index=0), panels[0]
    )


def test_standalone_link_annotation_requires_matching_text_and_bounds() -> None:
    line = SimpleNamespace(
        text="Return   to contents",
        words=(word("Return", left=10, top=20, native_index=0),),
    )
    page = SimpleNamespace(
        annots=[
            {"data": {"Subtype": "Text", "Contents": "Return to contents"}},
            {"data": {"Subtype": "Link", "Contents": "Different"}},
            {
                "data": {"Subtype": "Link", "Contents": b"Return to contents"},
                "x0": "bad",
            },
            {
                "data": {"Subtype": "/Link", "Contents": b"Return to contents"},
                "x0": 9,
                "top": 19,
                "x1": 31,
                "bottom": 31,
            },
        ]
    )

    assert _is_standalone_link_annotation(page, line)
    page.annots[-1]["x1"] = 20
    assert not _is_standalone_link_annotation(page, line)


def test_tagged_structure_reader_distinguishes_untagged_and_unreadable_pdf(
    tmp_path: Path,
) -> None:
    untagged = tmp_path / "untagged.pdf"
    write_blank_pdf(untagged)
    assert tagged_content_by_page(untagged) == ({}, None)

    unreadable = tmp_path / "unreadable.pdf"
    unreadable.write_bytes(b"not a pdf")
    content, error = tagged_content_by_page(unreadable)
    assert content == {}
    assert error is not None


def test_dependency_versions_degrades_missing_distribution_to_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from hhs_nofo_metrics.adapters import tagged_structure

    real_version = tagged_structure.importlib.metadata.version

    def version(distribution: str) -> str:
        if distribution == "pypdf":
            raise tagged_structure.importlib.metadata.PackageNotFoundError
        return real_version(distribution)

    monkeypatch.setattr(tagged_structure.importlib.metadata, "version", version)

    assert dependency_versions()["pypdf"] == "unknown"
    assert dependency_versions()["pdfplumber"] != "unknown"


def test_tagged_adapter_support_and_extract_fail_closed(tmp_path: Path) -> None:
    plugin = TaggedPdfAdapterPlugin()
    wrong_kind = SourceBundle(
        primary=SourceArtifact(name="primary", kind="html", source=b"<main />")
    )
    with materialize_source_bundle(wrong_kind) as materialized:
        support = plugin.inspect_support(materialized)
        assert support.status == "unsupported"
        assert "not pdf" in support.reason

    no_header = SourceBundle.from_pdf(b"not a pdf")
    with materialize_source_bundle(no_header) as materialized:
        support = plugin.inspect_support(materialized)
        assert support.status == "unsupported"
        assert support.reason == "Primary artifact has no PDF header."

    untagged = tmp_path / "untagged.pdf"
    write_blank_pdf(untagged)
    with materialize_source_bundle(SourceBundle.from_pdf(untagged)) as materialized:
        support = plugin.inspect_support(materialized)
        assert support.status == "unsupported"
        assert "no usable tagged structure" in support.reason
        with pytest.raises(AdapterContractError, match="does not accept configuration"):
            plugin.extract(materialized, config={"unexpected": True})
        with pytest.raises(AdapterContractError, match="no usable tagged structure"):
            plugin.extract(materialized, config={})

    with materialize_source_bundle(
        SourceBundle(
            primary=SourceArtifact(name="primary", kind="pdf", source=untagged),
            auxiliaries=(SourceArtifact(name="manifest", kind="json", source=b"{}"),),
        )
    ) as materialized:
        with pytest.raises(AdapterContractError, match="auxiliary artifacts"):
            plugin.extract(materialized, config={})

    inaccessible = MaterializedSourceBundle(
        primary=MaterializedArtifact(
            name="primary",
            kind="pdf",
            path=tmp_path,
            media_type="application/pdf",
            sha256="0" * 64,
            byte_length=0,
        )
    )
    support = plugin.inspect_support(inaccessible)
    assert support.status == "indeterminate"
