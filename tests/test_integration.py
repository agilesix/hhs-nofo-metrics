from __future__ import annotations

import json
import subprocess
import sys
from io import BytesIO, StringIO
from pathlib import Path

import pytest
from jsonschema import validate
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    BooleanObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)

import hhs_nofo_metrics.api as api_module
from hhs_nofo_metrics import (
    AdapterContractError,
    InputError,
    SourceBundle,
    __version__,
    analyze,
)
from hhs_nofo_metrics.adapters import (
    PdfAdapter,
    TaggedPdfAdapterPlugin,
    run_adapter_conformance,
)
from hhs_nofo_metrics.sources import materialize_source_bundle
from hhs_nofo_metrics.version import PACKAGE_VERSION

CLI = (sys.executable, "-m", "hhs_nofo_metrics_cli")


@pytest.mark.parametrize("shared_paragraph", [True, False])
@pytest.mark.parametrize("page_count", [2, 3])
@pytest.mark.parametrize("with_footer", [True, False])
def test_cross_page_paragraph_preserves_readability(
    tmp_path, shared_paragraph, page_count, with_footer
):
    writer = PdfWriter()
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    root = DictionaryObject({NameObject("/Type"): NameObject("/StructTreeRoot")})
    root_ref = writer._add_object(root)
    marks = []
    texts = ["Applications must be", "reviewed by staff. Submit complete forms."]
    if page_count == 3:
        texts = ["Applications must", "be reviewed by", "staff. Submit complete forms."]
    for index, text in enumerate(texts):
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        content = DecodedStreamObject()
        footer = "/Artifact BMC 0 -650 Td (Footer) Tj EMC" if with_footer else ""
        content.set_data(
            (
                f"BT /F1 10 Tf /P <</MCID 0>> BDC 72 700 Td ({text}) Tj EMC {footer} ET"
            ).encode()
        )
        page[NameObject("/Contents")] = writer._add_object(content)
        page[NameObject("/StructParents")] = NumberObject(index)
        marks.append(
            DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/MCR"),
                    NameObject("/Pg"): page.indirect_reference,
                    NameObject("/MCID"): NumberObject(0),
                }
            )
        )
    groups = [marks] if shared_paragraph else [[mark] for mark in marks]
    root[NameObject("/K")] = ArrayObject(
        [
            writer._add_object(
                DictionaryObject(
                    {
                        NameObject("/Type"): NameObject("/StructElem"),
                        NameObject("/S"): NameObject("/P"),
                        NameObject("/P"): root_ref,
                        NameObject("/K"): ArrayObject(group),
                    }
                )
            )
            for group in groups
        ]
    )
    writer.root_object[NameObject("/StructTreeRoot")] = root_ref
    path = tmp_path / "cross-page.pdf"
    writer.write(path)
    with materialize_source_bundle(SourceBundle.from_pdf(path)) as source:
        doc = TaggedPdfAdapterPlugin().extract(source, config={}).document
    body = [s for s in doc.segments if s.role == "body"]
    assert len(body) == (1 if shared_paragraph else page_count)
    locations = doc.metadata["cross_page_paragraph_locations"]
    if shared_paragraph:
        assert body[0].text == " ".join(texts)
        assert body[0].location.page == 1
        assert body[0].location.bbox is None
        assert [loc["page"] for loc in locations[body[0].id]] == list(
            range(1, page_count + 1)
        )
    else:
        assert not locations
    paragraphs = [" ".join(texts)] if shared_paragraph else texts
    html = "".join(f"<p>{text}</p>" for text in paragraphs).encode()
    expected = analyze(SourceBundle.from_html(html), profile="hhs-nofo-fy27-html@0.4.0")
    actual = analyze(path, profile="hhs-nofo-fy27-pdf-estimate@0.5.0")
    assert actual.coverage.pages_with_text == page_count
    if shared_paragraph:
        assert actual.metrics["words_per_sentence"].components["word_count"] == 9
        assert actual.metrics["words_per_sentence"].components["paragraph_count"] == 1
        assert (
            actual.metrics["passive_sentence_percentage"].components[
                "passive_sentence_count"
            ]
            == 1
        )
    for key in expected.metrics:
        assert expected.metrics[key].value is not None
        assert actual.metrics[key].value == expected.metrics[key].value
        assert actual.metrics[key].components == expected.metrics[key].components


def write_three_page_pdf(path: Path) -> None:
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_reference = writer._add_object(font)
    for page_number in range(1, 4):
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_reference})}
        )
        content = DecodedStreamObject()
        content.set_data(
            (
                "BT /F1 10 Tf 72 740 Td "
                f"(Repeated Notice 2026 Page {page_number}) Tj "
                "0 -40 Td (Applicants submit complete forms. Staff review each application.) Tj "
                "0 -680 Td (Repeated Footer 2026) Tj ET"
            ).encode("ascii")
        )
        page[NameObject("/Contents")] = writer._add_object(content)
    writer.add_metadata(
        {
            "/Title": "Synthetic parity fixture",
            "/Producer": "Tests",
            "/InternalReviewer": "Must not cross the package boundary",
        }
    )
    with path.open("wb") as stream:
        writer.write(stream)


def write_tagged_structured_pdf(
    path: Path,
    *,
    body_text: str = "Applicants submit complete forms.",
    second_tag: str = "/LBody",
    second_text: str = "Describe your proposed approach.",
    append_blank_page: bool = False,
) -> None:
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_reference = writer._add_object(font)
    page = writer.add_blank_page(width=612, height=792)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_reference})}
    )
    content = DecodedStreamObject()
    content.set_data(
        (
            "BT /F1 10 Tf "
            f"/P <</MCID 0>> BDC 1 0 0 1 72 700 Tm ({body_text}) Tj EMC "
            f"{second_tag} <</MCID 1>> BDC 1 0 0 1 72 660 Tm "
            f"({second_text}) Tj EMC "
            "/H2 <</MCID 2>> BDC 1 0 0 1 72 620 Tm (Application review.) Tj EMC ET"
        ).encode("ascii")
    )
    page[NameObject("/Contents")] = writer._add_object(content)

    structure_root = DictionaryObject(
        {NameObject("/Type"): NameObject("/StructTreeRoot")}
    )
    structure_root_reference = writer._add_object(structure_root)
    children = []
    for tag, mcid in (("/P", 0), (second_tag, 1), ("/H2", 2)):
        child = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/StructElem"),
                NameObject("/S"): NameObject(tag),
                NameObject("/P"): structure_root_reference,
                NameObject("/Pg"): page.indirect_reference,
                NameObject("/K"): NumberObject(mcid),
            }
        )
        children.append(writer._add_object(child))
    structure_root[NameObject("/K")] = ArrayObject(children)
    page[NameObject("/StructParents")] = NumberObject(0)
    writer.root_object[NameObject("/StructTreeRoot")] = structure_root_reference
    writer.root_object[NameObject("/MarkInfo")] = DictionaryObject(
        {NameObject("/Marked"): BooleanObject(True)}
    )
    if append_blank_page:
        writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Producer": "Synthetic tagged fixture"})
    with path.open("wb") as stream:
        writer.write(stream)


def test_generic_pdf_fallback_excludes_page_furniture_and_reports_low_reliability(
    tmp_path: Path,
) -> None:
    source = tmp_path / "fixture.pdf"
    write_three_page_pdf(source)

    result = analyze(
        source,
        profile="hhs-nofo-fy27-generic-pdf-estimate@0.4.0",
    )

    assert result.metrics["word_count"].status == "estimated"
    assert result.metrics["word_count"].reliability is not None
    assert result.metrics["word_count"].reliability.level == "low"
    assert "flat_pdf_semantic_structure_unavailable" in (
        result.metrics["word_count"].reliability.reason_codes
    )
    passive = result.metrics["passive_sentence_percentage"]
    assert passive.status == "estimated"
    assert passive.value == 0
    assert passive.reliability is not None
    assert passive.reliability.level == "low"
    assert any(
        warning.code == "flat_pdf_estimate_reliability_attached"
        and "reconstructed" in warning.message
        for warning in result.warnings
    )
    assert result.selection["word_count"].excluded_segment_count >= 6
    assert "Applicants submit complete forms" not in json.dumps(result.to_dict())
    assert result.source.observed_pdf_metadata == {
        "Producer": "Tests",
    }
    assert "InternalReviewer" not in json.dumps(result.to_dict())

    schema = json.loads(
        (
            Path(__file__).parents[1]
            / "src/hhs_nofo_metrics/schemas/analysis-result-1.2.0.json"
        ).read_text(encoding="utf-8")
    )
    validate(result.to_dict(), schema)


def test_tagged_pdf_blank_page_is_not_an_extraction_failure(tmp_path: Path) -> None:
    source = tmp_path / "tagged-with-blank-page.pdf"
    write_tagged_structured_pdf(source, append_blank_page=True)

    result = analyze(source, profile="hhs-nofo-fy27-pdf-estimate@0.5.0")

    assert result.coverage.page_count == 2
    assert result.coverage.pages_extracted == 2
    assert result.coverage.pages_with_text == 1
    assert result.coverage.extraction_error_pages == ()
    assert all(
        metric.reliability is not None
        and "page_extraction_incomplete" not in metric.reliability.reason_codes
        for metric in result.metrics.values()
    )


@pytest.mark.parametrize("supporting_pages", [1, 2])
def test_tagged_pdf_running_navigation_exclusion_preserves_instructions(
    tmp_path: Path, supporting_pages: int
) -> None:
    """Exercise real PDF marks, geometry, adapter grouping and profile selection."""
    writer = PdfWriter()
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    root = DictionaryObject({NameObject("/Type"): NameObject("/StructTreeRoot")})
    root_ref = writer._add_object(root)
    children = []
    for index in range(supporting_pages + 1):
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        content = DecodedStreamObject()
        nav_mark = "/LBody <</MCID 0>> BDC" if index == 0 else "/Artifact BMC"
        content.set_data(
            (
                f"BT /F1 10 Tf {nav_mark} 1 0 0 1 72 778 Tm (Review) Tj EMC "
                "/P <</MCID 1>> BDC 1 0 0 1 72 700 Tm "
                "(Before You Begin. Review the application instructions.) Tj EMC ET"
            ).encode("ascii")
        )
        page[NameObject("/Contents")] = writer._add_object(content)
        page[NameObject("/StructParents")] = NumberObject(index)
        tags = [("/P", 1)] + ([("/LBody", 0)] if index == 0 else [])
        for tag, mcid in tags:
            children.append(
                writer._add_object(
                    DictionaryObject(
                        {
                            NameObject("/Type"): NameObject("/StructElem"),
                            NameObject("/S"): NameObject(tag),
                            NameObject("/P"): root_ref,
                            NameObject("/Pg"): page.indirect_reference,
                            NameObject("/K"): NumberObject(mcid),
                        }
                    )
                )
            )
    root[NameObject("/K")] = ArrayObject(children)
    writer.root_object[NameObject("/StructTreeRoot")] = root_ref
    source = tmp_path / "running-navigation.pdf"
    writer.write(source)

    with materialize_source_bundle(SourceBundle.from_pdf(source)) as materialized:
        segments = (
            TaggedPdfAdapterPlugin().extract(materialized, config={}).document.segments
        )
    top = next(s for s in segments if s.location.page == 1 and s.text == "Review")
    assert top.role == ("navigation" if supporting_pages == 2 else "list")
    instructions = [s for s in segments if s.text.startswith("Before You Begin.")]
    assert len(instructions) == supporting_pages + 1
    assert all(s.role == "body" for s in instructions)
    result = analyze(source, profile="hhs-nofo-fy27-pdf-estimate@0.5.0")
    assert result.metrics["word_count"].value == (
        7 * (supporting_pages + 1) + (1 if supporting_pages == 1 else 0)
    )

    # Compare identical reader-facing content through the public HTML and PDF
    # paths. Insufficient PDF artifact evidence deliberately retains one nav word.
    html = (
        '<div id="download_target"><nav>Review</nav>'
        + "<p>Before You Begin. Review the application instructions.</p>"
        * (supporting_pages + 1)
        + "</div>"
    )
    html_result = analyze(
        SourceBundle.from_html(html.encode()),
        profile="hhs-nofo-fy27-html@0.4.0",
        adapter_config={"root_id": "download_target"},
        production_path="nofo_builder_export_html",
    )
    assert result.metrics["word_count"].value - html_result.metrics[
        "word_count"
    ].value == (1 if supporting_pages == 1 else 0)
    for metric_id, html_metric in html_result.metrics.items():
        if metric_id == "word_count":
            continue
        assert html_metric.value is not None, metric_id
        assert result.metrics[metric_id].value == html_metric.value, metric_id
        assert result.metrics[metric_id].components == html_metric.components, metric_id


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    (("document_id", ""), ("revision", "  ")),
)
def test_python_api_rejects_empty_optional_source_identifiers(
    tmp_path: Path,
    field_name: str,
    field_value: str,
) -> None:
    source = tmp_path / "fixture.pdf"
    write_three_page_pdf(source)

    with pytest.raises(InputError, match=field_name):
        analyze(
            source,
            profile="hhs-nofo-fy27-generic-pdf-estimate@0.4.0",
            **{field_name: field_value},
        )


def test_runtime_package_and_engine_versions_share_one_identity() -> None:
    assert __version__ == PACKAGE_VERSION


def test_python_api_accepts_path_bytes_and_binary_stream(tmp_path: Path) -> None:
    source = tmp_path / "fixture.pdf"
    write_three_page_pdf(source)
    payload = source.read_bytes()

    profile = "hhs-nofo-fy27-generic-pdf-estimate@0.4.0"
    path_result = analyze(source, profile=profile)
    bytes_result = analyze(payload, profile=profile)
    stream = BytesIO(payload)
    stream.seek(10)
    stream_result = analyze(stream, profile=profile)

    assert path_result.source.sha256 == bytes_result.source.sha256
    assert bytes_result.source.sha256 == stream_result.source.sha256
    assert path_result.source.byte_length == len(payload)
    assert bytes_result.source.byte_length == len(payload)
    assert stream.tell() == 10
    assert {
        metric_id: metric.to_dict() for metric_id, metric in path_result.metrics.items()
    } == {
        metric_id: metric.to_dict()
        for metric_id, metric in bytes_result.metrics.items()
    }


def test_generic_pdf_profile_default_adapter_matches_explicit_pdf_adapter(
    tmp_path: Path,
) -> None:
    source = tmp_path / "fixture.pdf"
    write_three_page_pdf(source)

    profile = "hhs-nofo-fy27-generic-pdf-estimate@0.4.0"
    implicit = analyze(source, profile=profile)
    explicit = analyze(
        source,
        profile=profile,
        adapter="pdf",
    )

    implicit_payload = implicit.to_dict()
    explicit_payload = explicit.to_dict()
    for payload in (implicit_payload, explicit_payload):
        payload.pop("analysis_id")
        payload.pop("generated_at")
    assert implicit_payload == explicit_payload


def test_python_api_requires_an_explicit_profile(tmp_path: Path) -> None:
    source = tmp_path / "fixture.pdf"
    write_three_page_pdf(source)

    with pytest.raises(TypeError, match="profile"):
        analyze(source)  # type: ignore[call-arg]


def test_semantic_html_and_tagged_pdf_estimate_share_metric_kernel(
    tmp_path: Path,
) -> None:
    source = tmp_path / "tagged.pdf"
    write_tagged_structured_pdf(
        source,
        body_text="You must submit complete forms.",
        second_tag="/P",
    )
    html = b"""<!doctype html><html><body><main id="download_target">
      <p>You must submit complete forms.</p>
      <ul><li>Describe your proposed approach.</li></ul>
      <h2>Application review.</h2>
    </main></body></html>"""

    html_result = analyze(
        SourceBundle.from_html(html),
        profile="hhs-nofo-fy27-html@0.4.0",
        adapter_config={"root_id": "download_target"},
    )
    pdf_result = analyze(source, profile="hhs-nofo-fy27-pdf-estimate@0.5.0")

    assert "hhs-nofo-fy27-pdf-estimate@0.5.0" in api_module.list_profiles()
    assert pdf_result.adapter.id == "hhs-tagged-pdf-adapter"
    assert pdf_result.result_basis == "structured_estimate"
    assert pdf_result.source.observed_pdf_metadata == {
        "Producer": "Synthetic tagged fixture"
    }
    assert pdf_result.coverage.page_count == 1
    assert pdf_result.coverage.pages_extracted == 1
    assert pdf_result.coverage.unknown_role_count == 0

    for metric_id in (
        "word_count",
        "words_per_sentence",
        "characters_per_word",
        "flesch_reading_ease",
        "flesch_kincaid_grade_level",
        "passive_sentence_percentage",
    ):
        assert html_result.metrics[metric_id].status == "calculated"
        assert pdf_result.metrics[metric_id].status == "estimated"
        assert pdf_result.metrics[metric_id].reliability is not None
        assert (
            html_result.metrics[metric_id].value == pdf_result.metrics[metric_id].value
        )
    assert html_result.metrics["words_per_sentence"].components["sentence_count"] == 2
    assert pdf_result.metrics["words_per_sentence"].components["sentence_count"] == 2


def test_tagged_pdf_adapter_passes_shared_conformance_contract(
    tmp_path: Path,
) -> None:
    source = tmp_path / "tagged.pdf"
    write_tagged_structured_pdf(source)

    with materialize_source_bundle(SourceBundle.from_pdf(source)) as materialized:
        report = run_adapter_conformance(
            TaggedPdfAdapterPlugin(),
            materialized,
        )

    assert report.to_dict()["conformant"] is True


def test_tagged_pdf_estimate_rejects_untagged_pdf(tmp_path: Path) -> None:
    source = tmp_path / "untagged.pdf"
    write_three_page_pdf(source)

    with pytest.raises(
        AdapterContractError,
        match="no usable tagged structure groups",
    ):
        analyze(source, profile="hhs-nofo-fy27-pdf-estimate@0.5.0")


def test_pdf_estimate_reports_metrics_with_reliability_for_unknown_content(
    tmp_path: Path,
) -> None:
    source = tmp_path / "partially-tagged.pdf"
    write_tagged_structured_pdf(source, second_tag="/Span")

    result = analyze(source, profile="hhs-nofo-fy27-pdf-estimate@0.5.0")
    payload = result.to_dict()

    assert "hhs-nofo-fy27-pdf-estimate@0.5.0" in api_module.list_profiles()
    assert payload["schema_version"] == "1.2.0"
    assert payload["coverage"]["unknown_role_count"] == 1
    for metric_id in (
        "word_count",
        "words_per_sentence",
        "characters_per_word",
        "flesch_reading_ease",
        "flesch_kincaid_grade_level",
        "passive_sentence_percentage",
    ):
        metric = payload["metrics"][metric_id]
        assert metric["status"] == "estimated"
        assert metric["reliability"]["level"] in {"moderate", "low"}
        assert metric["reliability"]["unknown_segment_count"] == 1
        assert metric["reliability"]["unknown_word_count"] == 4

    schema = json.loads(
        (
            Path(__file__).parents[1]
            / "src/hhs_nofo_metrics/schemas/analysis-result-1.2.0.json"
        ).read_text(encoding="utf-8")
    )
    validate(payload, schema)


def test_pdf_estimate_is_high_reliability_for_zero_word_unknown_segment(
    tmp_path: Path,
) -> None:
    source = tmp_path / "word-style-tagged.pdf"
    write_tagged_structured_pdf(source, second_tag="/Span", second_text=".")

    result = analyze(source, profile="hhs-nofo-fy27-pdf-estimate@0.5.0")

    for metric_id in (
        "word_count",
        "words_per_sentence",
        "characters_per_word",
        "flesch_reading_ease",
        "flesch_kincaid_grade_level",
        "passive_sentence_percentage",
    ):
        metric = result.metrics[metric_id]
        assert metric.status == "estimated"
        assert metric.reliability is not None
        assert metric.reliability.level == "high"
        assert metric.reliability.unknown_word_count == 0
        assert metric.reliability.sensitivity.absolute_delta == 0


def test_pdf_estimate_is_high_reliability_for_complete_tagged_scope(
    tmp_path: Path,
) -> None:
    source = tmp_path / "tagged.pdf"
    write_tagged_structured_pdf(source)

    result = analyze(source, profile="hhs-nofo-fy27-pdf-estimate@0.5.0")

    assert result.coverage.classification_coverage == 1.0
    assert result.coverage.unknown_role_count == 0
    assert result.metrics["word_count"].reliability is not None
    assert result.metrics["word_count"].reliability.level == "high"
    assert result.metrics["word_count"].reliability.reason_codes == (
        "complete_resolved_role_scope",
        "unknown_policy_sensitivity_negligible",
    )


def test_pdf_estimate_rejects_untagged_pdf(tmp_path: Path) -> None:
    source = tmp_path / "untagged.pdf"
    write_three_page_pdf(source)

    with pytest.raises(
        AdapterContractError,
        match="no usable tagged structure groups",
    ):
        analyze(source, profile="hhs-nofo-fy27-pdf-estimate@0.5.0")


def test_python_api_rejects_nonbinary_stream_with_stable_error() -> None:
    with pytest.raises(InputError) as caught:
        analyze(
            StringIO("not a binary PDF"),  # type: ignore[arg-type]
            profile="hhs-nofo-fy27-generic-pdf-estimate@0.4.0",
        )

    assert caught.value.to_dict() == {
        "code": "input_error",
        "message": "PDF stream must return bytes",
    }


def test_pdf_adapter_adds_geometry_without_changing_line_text(tmp_path: Path) -> None:
    source = tmp_path / "geometry.pdf"
    write_three_page_pdf(source)

    document = PdfAdapter().extract(source)
    geometry = document.metadata["line_geometry"]

    assert geometry["total_line_count"] == len(document.segments)
    assert geometry["matched_line_count"] == len(document.segments)
    assert all(segment.location.bbox is not None for segment in document.segments)
    assert any(
        "Applicants submit complete forms" in segment.text
        for segment in document.segments
    )


def test_cli_writes_json_result(tmp_path: Path) -> None:
    source = tmp_path / "fixture.pdf"
    output = tmp_path / "result.json"
    write_three_page_pdf(source)

    completed = subprocess.run(
        [
            *CLI,
            "analyze",
            str(source),
            "--profile",
            "hhs-nofo-fy27-generic-pdf-estimate@0.4.0",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["profile"]["id"] == "hhs-nofo-fy27-generic-pdf-estimate"


def test_cli_analyzes_semantic_html_source(tmp_path: Path) -> None:
    source = tmp_path / "export.html"
    config = tmp_path / "html-adapter.json"
    output = tmp_path / "html-result.json"
    source.write_text(
        '<main id="download_target"><h1>Apply now</h1>'
        "<p>Applicants submit forms.</p></main>",
        encoding="utf-8",
    )
    config.write_text('{"root_id":"download_target"}', encoding="utf-8")

    completed = subprocess.run(
        [
            *CLI,
            "analyze",
            str(source),
            "--source-kind",
            "html",
            "--profile",
            "hhs-nofo-fy27-html@0.4.0",
            "--adapter-config",
            str(config),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["source"]["kind"] == "html"
    assert result["adapter"]["id"] == "hhs-semantic-html-adapter"
    assert result["metrics"]["word_count"]["value"] == 5
    assert result["metrics"]["words_per_sentence"]["value"] == 3


@pytest.mark.parametrize("flag", ("-v", "-V", "--version"))
def test_cli_version_fast_paths_are_consistent(flag: str) -> None:
    completed = subprocess.run(
        [*CLI, flag], check=False, capture_output=True, text=True
    )

    assert completed.returncode == 0
    assert completed.stdout.strip() == __version__
    assert completed.stderr == ""


def test_fast_cli_entry_does_not_import_pdf_runtime() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import hhs_nofo_metrics_cli; "
                "print(','.join(name for name in "
                "('hhs_nofo_metrics.api','pdfplumber','pypdf') "
                "if name in sys.modules))"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert completed.stdout == "\n"
    assert completed.stderr == ""


def test_cli_without_arguments_returns_content_first_home() -> None:
    completed = subprocess.run(CLI, check=False, capture_output=True, text=True)

    assert completed.returncode == 0
    assert "description: Calculate versioned HHS NOFO readability metrics." in (
        completed.stdout
    )
    assert "profiles[3]:" in completed.stdout
    assert "adapters[3]{reference,source_kinds,capability_count}:" in completed.stdout
    assert "help[3]:" in completed.stdout
    assert completed.stderr == ""


def test_cli_usage_errors_are_structured() -> None:
    completed = subprocess.run(
        [*CLI, "unknown"], check=False, capture_output=True, text=True
    )

    assert completed.returncode == 2
    assert "code: usage_error" in completed.stdout
    assert "usage:" in completed.stdout
    assert completed.stderr == ""

    json_completed = subprocess.run(
        [*CLI, "unknown", "--json"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert json_completed.returncode == 2
    assert json.loads(json_completed.stdout)["error"]["code"] == "usage_error"
    assert json_completed.stderr == ""


def test_cli_requires_an_explicit_profile(tmp_path: Path) -> None:
    source = tmp_path / "fixture.pdf"
    output = tmp_path / "result.json"
    write_three_page_pdf(source)

    completed = subprocess.run(
        [
            *CLI,
            "analyze",
            str(source),
            "--output",
            str(output),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["error"]["code"] == "usage_error"
    assert "--profile" in payload["error"]["message"]
    assert not output.exists()
    assert completed.stderr == ""
