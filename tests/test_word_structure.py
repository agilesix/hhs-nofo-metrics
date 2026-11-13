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
