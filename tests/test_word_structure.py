from xml.etree.ElementTree import fromstring

from hhs_nofo_metrics.adapters.word_structure import (
    WordFrontMatter,
    recognize_front_matter,
)


def recognize(*blocks):
    body = fromstring(
        '<w:body xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        + "".join(blocks)
        + "</w:body>"
    )
    return recognize_front_matter(body)


def paragraph(text, style=None, section=False):
    props = (f'<w:pStyle w:val="{style}"/>' if style else "") + (
        "<w:sectPr/>" if section else ""
    )
    return f"<w:p><w:pPr>{props}</w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>"


def gallery(name):
    return (
        "<w:sdt><w:sdtPr><w:docPartObj>"
        f'<w:docPartGallery w:val="{name}"/>'
        "</w:docPartObj></w:sdtPr><w:sdtContent>"
        + paragraph("Structured content")
        + "</w:sdtContent></w:sdt>"
    )


def test_galleries_styles_and_unmarked_lookalikes():
    assert recognize(
        gallery("Cover Pages"),
        paragraph("Contents", "TOCHeading"),
        paragraph("Eligibility 3", "TOC1"),
        gallery("Table of Contents"),
        paragraph("Eligibility 3"),
    ) == {
        0: WordFrontMatter("cover", "gallery"),
        1: WordFrontMatter("table_of_contents", "label"),
        2: WordFrontMatter("table_of_contents", "style"),
        3: WordFrontMatter("table_of_contents", "gallery"),
    }


def test_position_needs_next_heading_or_toc_and_no_earlier_heading():
    first = paragraph("Draft title", section=True)
    assert recognize(first, paragraph("Eligibility", "Heading1")) == {
        0: WordFrontMatter("cover", "position")
    }
    assert recognize(first, paragraph("Eligibility")) == {}
    assert (
        recognize(
            paragraph("Earlier heading", "Heading1"),
            first,
            paragraph("Another heading", "Heading2"),
        )
        == {}
    )


def test_complex_toc_uses_completed_field_not_label_text():
    start = (
        '<w:p><w:r><w:fldChar w:fldCharType="begin"/>'
        '<w:instrText> TOC </w:instrText><w:fldChar w:fldCharType="separate"/>'
        "</w:r></w:p>"
    )
    end = '<w:p><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
    assert recognize(start, paragraph("Eligibility 3"), end, paragraph("Body")) == {
        1: WordFrontMatter("table_of_contents", "field")
    }
    assert recognize(start, paragraph("Eligibility 3"), paragraph("Body")) == {}


def test_simple_toc_field_does_not_exclude_shared_applicant_prose():
    field = (
        '<w:fldSimple w:instr=" TOC "><w:r><w:t>Eligibility 3</w:t></w:r></w:fldSimple>'
    )
    assert recognize(f"<w:p>{field}</w:p>") == {
        0: WordFrontMatter("table_of_contents", "field")
    }
    assert recognize(f"<w:p>{field}<w:r><w:t>Apply today.</w:t></w:r></w:p>") == {}


def test_generated_metadata_needs_basic_information_context():
    label = paragraph("Metadata author: Example agency")
    assert recognize(label) == {}
    assert recognize(
        paragraph("Basic information", "Heading3"),
        paragraph("OpDiv: Example"),
        paragraph("Opportunity number: TEST"),
        label,
        paragraph("Eligibility", "Heading3"),
        label,
    ) == {3: WordFrontMatter("metadata", "builder")}


def test_instruction_table_requires_one_cell_and_an_explicit_template_label():
    for label in (
        "Instructions for NOFO writers",
        "Instructions for template managers",
        "Instructions for new NOFO team",
        "Agency-specific instructions",
    ):
        cell = f"<w:tc>{paragraph(label)}{paragraph('Writer guidance.')}</w:tc>"
        table = f"<w:tbl><w:tr>{cell}</w:tr></w:tbl>"
        assert recognize(paragraph(label), table) == {
            1: WordFrontMatter("instruction", "table")
        }
        assert recognize(f"<w:tbl><w:tr>{cell}{cell}</w:tr></w:tbl>") == {}
    assert (
        recognize(
            f"<w:tbl><w:tr><w:tc>{paragraph('Instructions for applicants')}</w:tc></w:tr></w:tbl>"
        )
        == {}
    )
