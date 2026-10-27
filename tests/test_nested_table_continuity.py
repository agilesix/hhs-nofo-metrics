"""Synthetic PDF fixtures: source-declared table blocks, never visual guessing."""

from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)

from hhs_nofo_metrics import SourceBundle, analyze
from hhs_nofo_metrics.adapters.tagged_pdf import TaggedPdfAdapterPlugin
from hhs_nofo_metrics.sources import materialize_source_bundle


@pytest.fixture
def table_pdf(tmp_path):
    """Build a real two-page tagged PDF from (tag, children)/(page, text) nodes.

    Text operators and MCIDs are page-local; the indirect semantic block is
    shared only when the test explicitly gives it children on both pages.
    """

    def write(cells, *, inherited_page_marks=False) -> Path:
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
        pages = [writer.add_blank_page(width=612, height=792) for _ in range(2)]
        streams = [[], []]
        root = DictionaryObject({NameObject("/Type"): NameObject("/StructTreeRoot")})
        root_ref = writer._add_object(root)

        def node(spec, parent):
            tag, children = spec
            value = DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/StructElem"),
                    NameObject("/S"): NameObject("/" + tag),
                    NameObject("/P"): parent,
                }
            )
            ref = writer._add_object(value)
            marks = []
            for child in children:
                if isinstance(child[0], str):
                    marks.append(node(child, ref))
                    continue
                page_number, text = child
                index = page_number - 1
                mcid = len(streams[index])
                streams[index].append(
                    f"/{tag} <</MCID {mcid}>> BDC BT /F1 10 Tf "
                    f"72 {700 - 24 * mcid} Td ({text}) Tj ET EMC"
                )
                if inherited_page_marks:
                    marks.append(
                        writer._add_object(
                            DictionaryObject(
                                {
                                    NameObject("/Type"): NameObject("/StructElem"),
                                    NameObject("/S"): NameObject("/Span"),
                                    NameObject("/P"): ref,
                                    NameObject("/Pg"): pages[index].indirect_reference,
                                    NameObject("/K"): NumberObject(mcid),
                                }
                            )
                        )
                    )
                    continue
                marks.append(
                    DictionaryObject(
                        {
                            NameObject("/Type"): NameObject("/MCR"),
                            NameObject("/Pg"): pages[index].indirect_reference,
                            NameObject("/MCID"): NumberObject(mcid),
                        }
                    )
                )
            value[NameObject("/K")] = ArrayObject(marks)
            return ref

        root[NameObject("/K")] = ArrayObject(
            [node(("Document", [("Table", [("TR", cells)])]), root_ref)]
        )
        writer.root_object[NameObject("/StructTreeRoot")] = root_ref
        for index, page in enumerate(pages):
            page[NameObject("/Resources")] = DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
            )
            page[NameObject("/StructParents")] = NumberObject(index)
            content = DecodedStreamObject()
            content.set_data("\n".join(streams[index]).encode("ascii"))
            page[NameObject("/Contents")] = writer._add_object(content)
        path = tmp_path / "synthetic-nested-table.pdf"
        writer.write(path)
        return path

    return write


def extract(path):
    with materialize_source_bundle(SourceBundle.from_pdf(path)) as source:
        return TaggedPdfAdapterPlugin().extract(source, config={}).document


@pytest.mark.parametrize("inherited_page_marks", [False, True])
@pytest.mark.parametrize("cell_tag", ["TD", "TH"])
@pytest.mark.parametrize("inline_span", [False, True])
@pytest.mark.parametrize(
    "profile",
    [
        "hhs-nofo-fy27-pdf-estimate@0.5.0",
        "hhs-nofo-fy27-pdf-estimate@0.6.0",
    ],
)
def test_nested_paragraph_continuity_has_independent_metric_reference(
    table_pdf, cell_tag, inline_span, profile, inherited_page_marks
):
    parts = [
        (1, "Applications must be"),
        (2, "reviewed by staff. Submit complete forms."),
    ]
    children = [("Span", [part]) for part in parts] if inline_span else parts
    path = table_pdf(
        [(cell_tag, [("P", children)])], inherited_page_marks=inherited_page_marks
    )
    doc = extract(path)
    assert [s.text for s in doc.segments] == [
        "Applications must be reviewed by staff. Submit complete forms."
    ]
    segment = doc.segments[0]
    assert segment.location.page == 1
    assert segment.location.bbox is None
    locations = doc.metadata["cross_page_paragraph_locations"][segment.id]
    assert [loc["page"] for loc in locations] == [1, 2]
    assert all("bbox" in loc for loc in locations)

    # Independent reference: 9 words; sentences contain 6 and 3 words;
    # one paragraph; the first sentence is passive. The word syllables are
    # 4,1,1,2,1,1,2,2,1 (15 total). FK = .39*(9/2)+11.8*(15/9)-15.59.
    result = analyze(path, profile=profile)
    assert result.metrics["word_count"].value == 9
    counts = result.metrics["words_per_sentence"].components
    assert counts["word_count"] == 9
    assert counts["sentence_count"] == 2
    assert counts["paragraph_count"] == 1
    assert counts["sentences_per_paragraph"] == 2
    assert result.metrics["words_per_sentence"].value == 4.5
    grade = result.metrics["flesch_kincaid_grade_level"]
    assert grade.components["syllable_count"] == 15
    assert grade.value == 5.83
    passive = result.metrics["passive_sentence_percentage"]
    assert passive.components["passive_sentence_count"] == 1
    assert passive.components["sentence_count"] == 2
    assert passive.value == 50


@pytest.mark.parametrize("cell_tag", ["TD", "TH"])
def test_separate_paragraphs_in_one_cell_keep_boundaries(table_pdf, cell_tag):
    path = table_pdf(
        [
            (
                cell_tag,
                [
                    ("P", [(1, "Applications must be")]),
                    ("P", [(1, "reviewed by staff.")]),
                    ("P", [(2, "Submit complete forms.")]),
                ],
            )
        ]
    )
    doc = extract(path)
    assert [s.text for s in doc.segments] == [
        "Applications must be",
        "reviewed by staff.",
        "Submit complete forms.",
    ]
    assert not doc.metadata["cross_page_paragraph_locations"]
    result = analyze(path, profile="hhs-nofo-fy27-pdf-estimate@0.5.0")
    # The incomplete first paragraph must not be joined to the second.
    assert result.metrics["word_count"].value == 9
    counts = result.metrics["words_per_sentence"].components
    assert counts["word_count"] == 6
    assert counts["sentence_count"] == 2
    assert counts["paragraph_count"] == 2
    assert counts["sentences_per_paragraph"] == 1
    assert result.metrics["passive_sentence_percentage"].value == 0


@pytest.mark.parametrize("heading", ["H", "H1", "H2", "H7"])
def test_nested_headings_are_separate_from_continuing_paragraph(table_pdf, heading):
    path = table_pdf(
        [
            (
                "TD",
                [
                    (heading, [(1, "First heading"), (2, "Second heading")]),
                    ("P", [(1, "Applications must be"), (2, "reviewed by staff.")]),
                    ("P", [(2, "Submit complete forms.")]),
                ],
            )
        ]
    )
    doc = extract(path)
    assert [s.text for s in doc.segments] == [
        "First heading",
        "Applications must be reviewed by staff.",
        "Second heading",
        "Submit complete forms.",
    ]
    # Table scope is retained, but a heading never participates in paragraph repair.
    assert all(s.role == "table" for s in doc.segments)
    assert len(doc.metadata["cross_page_paragraph_locations"]) == 1
    result = analyze(path, profile="hhs-nofo-fy27-pdf-estimate@0.5.0")
    assert result.metrics["word_count"].value == 13
    counts = result.metrics["words_per_sentence"].components
    assert counts["word_count"] == 9
    assert counts["sentence_count"] == 2
    assert counts["paragraph_count"] == 2


def test_adjacent_cells_and_their_paragraphs_have_distinct_identities(table_pdf):
    path = table_pdf(
        [
            ("TD", [("P", [(1, "Applications must be")])]),
            ("TD", [("P", [(2, "reviewed by staff.")])]),
        ]
    )
    doc = extract(path)
    assert [s.text for s in doc.segments] == [
        "Applications must be",
        "reviewed by staff.",
    ]
    assert not doc.metadata["cross_page_paragraph_locations"]
    result = analyze(path, profile="hhs-nofo-fy27-pdf-estimate@0.5.0")
    assert result.metrics["word_count"].value == 6
    assert result.metrics["words_per_sentence"].components["word_count"] == 3
    assert result.metrics["passive_sentence_percentage"].value == 0


def test_mixed_direct_cell_content_is_not_joined_across_nested_block(table_pdf):
    path = table_pdf(
        [
            (
                "TD",
                [
                    (1, "Applications must be"),
                    ("P", [(1, "Separate paragraph.")]),
                    (2, "reviewed by staff."),
                ],
            )
        ]
    )
    doc = extract(path)
    assert [s.text for s in doc.segments] == [
        "Applications must be",
        "Separate paragraph.",
        "reviewed by staff.",
    ]
    assert not doc.metadata["cross_page_paragraph_locations"]


@pytest.mark.parametrize("inline_span", [False, True])
def test_direct_cell_continuity_stays_supported(table_pdf, inline_span):
    parts = [(1, "Applications must be"), (2, "reviewed by staff.")]
    children = [("Span", [part]) for part in parts] if inline_span else parts
    doc = extract(table_pdf([("TD", children)]))
    assert [s.text for s in doc.segments] == ["Applications must be reviewed by staff."]
    assert len(doc.metadata["cross_page_paragraph_locations"]) == 1


@pytest.mark.parametrize(
    "tag,role",
    [
        ("LBody", "list"),
        ("Note", "body"),
        ("Caption", "heading"),
        ("TOCI", "table_of_contents"),
    ],
)
def test_other_nested_containers_retain_existing_scope(table_pdf, tag, role):
    path = table_pdf([("TD", [(tag, [("P", [(1, "Existing container scope.")])])])])
    doc = extract(path)
    assert [s.text for s in doc.segments] == ["Existing container scope."]
    assert doc.segments[0].role == role
