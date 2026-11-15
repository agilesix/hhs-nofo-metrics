from xml.etree.ElementTree import fromstring

from hhs_nofo_metrics.adapters.word_structure import (
    WordFrontMatter,
    mark_word_scope,
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


def test_section_break_preserves_opening_applicant_prose():
    opening = paragraph(
        "Eligible applicants must serve rural communities.", section=True
    )
    assert recognize(opening, paragraph("Eligibility", "Heading1")) == {}
    assert recognize(opening, gallery("Table of Contents")) == {
        1: WordFrontMatter("table_of_contents", "gallery")
    }


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
    style = '<w:pPr><w:pStyle w:val="TOC1"/></w:pPr>'
    prose = "<w:r><w:t>Apply today.</w:t></w:r>"
    assert recognize(f"<w:p>{style}{field}{prose}</w:p>") == {}


def test_complex_field_keeps_mixed_boundaries_and_excludes_whole_results():
    start = (
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        "<w:r><w:instrText> TOC </w:instrText></w:r>"
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    )
    end = '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    entry = "<w:r><w:t>Eligibility 3</w:t></w:r>"
    prose = "<w:r><w:t>Applicants should apply.</w:t></w:r>"
    toc_style = '<w:pPr><w:pStyle w:val="TOC1"/></w:pPr>'
    assert recognize(f"<w:p>{start}{entry}{end}</w:p>") == {
        0: WordFrontMatter("table_of_contents", "field")
    }
    assert recognize(f"<w:p>{start}{entry}</w:p>", f"<w:p>{entry}{end}</w:p>") == {
        0: WordFrontMatter("table_of_contents", "field"),
        1: WordFrontMatter("table_of_contents", "field"),
    }
    assert recognize(
        f"<w:p>{toc_style}{prose}{start}{entry}</w:p>",
        paragraph("How to apply 4", "TOC1"),
        f"<w:p>{toc_style}{entry}{end}{prose}</w:p>",
    ) == {1: WordFrontMatter("table_of_contents", "style")}


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


def cover_lines():
    return (
        paragraph("Notice of Funding Opportunity"),
        paragraph("Application due 01/01/2099"),
        paragraph(" "),
        paragraph("Example Bureau"),
        paragraph("Example Program (EXP)"),
        paragraph("Opportunity Number: TEST-00-000", section=True),
    )


def toc_entries():
    return (
        paragraph("Table of Contents", "MainHeading"),
        paragraph("Basic information 3", "TOC2"),
        paragraph("Eligibility 4", "TOC2"),
    )


def test_leading_cover_section_before_contents_is_recognized_by_position():
    cover = WordFrontMatter("cover_position", "section")
    contents = WordFrontMatter("table_of_contents", "style")
    # The whitespace-only paragraph (2) is never marked, and the label
    # paragraph before the first contents entry (6) stays countable.
    assert recognize(*cover_lines(), *toc_entries()) == {
        0: cover,
        1: cover,
        3: cover,
        4: cover,
        5: cover,
        7: contents,
        8: contents,
    }
    # A gallery contents block directly after the section break also qualifies.
    roles = recognize(*cover_lines(), gallery("Table of Contents"))
    assert {i for i, r in roles.items() if r == cover} == {0, 1, 3, 4, 5}


def test_leading_section_stays_countable_unless_every_condition_holds():
    sentence = paragraph("Eligible applicants must serve rural communities.")
    heading = paragraph("Program overview", "Heading1")
    long_line = paragraph(" ".join(["word"] * 26))
    table = f"<w:tbl><w:tr><w:tc>{paragraph('Example Bureau')}</w:tc></w:tr></w:tbl>"
    many = [paragraph(" ".join(["word"] * 20)) for _ in range(6)]
    closing = paragraph("Opportunity Number: TEST-00-000", section=True)
    for opening in ([sentence], [heading], [long_line], [table], many):
        roles = recognize(*opening, closing, *toc_entries())
        assert not any(r.role == "cover_position" for r in roles.values())
    # No section break, or no contents after it, leaves the lines countable.
    no_break = [paragraph("Notice of Funding Opportunity"), *toc_entries()]
    assert not any(r.role == "cover_position" for r in recognize(*no_break).values())
    assert recognize(*cover_lines()) == {}
    no_contents = (*cover_lines(), paragraph("Program overview", "Heading1"))
    assert recognize(*no_contents) == {}
    # Two unrecognized paragraphs before the contents are not a label.
    roles = recognize(*cover_lines(), paragraph("Intro"), *toc_entries())
    assert not any(r.role == "cover_position" for r in roles.values())


def test_gallery_cover_keeps_its_existing_recognition():
    roles = recognize(
        gallery("Cover Pages"), paragraph("Break", section=True), *toc_entries()
    )
    assert roles[0] == WordFrontMatter("cover", "gallery")
    assert not any(r.role == "cover_position" for r in roles.values())


def test_generated_metadata_under_before_you_begin_heading():
    label = paragraph("Metadata author: Example agency")
    assert recognize(
        paragraph("Before You Begin", "Heading2"),
        paragraph("OpDiv: Example"),
        paragraph("Agency: Example"),
        paragraph("Opportunity number: TEST"),
        label,
        paragraph("Metadata keywords: Example; Test"),
        paragraph("Step 1: Review the Opportunity", "Heading1"),
        label,
    ) == {
        4: WordFrontMatter("metadata", "builder"),
        5: WordFrontMatter("metadata", "builder"),
    }
    # Other headings, or a run without the OpDiv/opportunity number pattern,
    # leave the labels countable.
    assert (
        recognize(
            paragraph("Program overview", "Heading2"),
            paragraph("OpDiv: Example"),
            paragraph("Opportunity number: TEST"),
            label,
        )
        == {}
    )
    assert (
        recognize(paragraph("Before You Begin", "Heading2"), paragraph("Intro"), label)
        == {}
    )
    # The label inside a sentence of body prose is not a metadata line.
    assert (
        recognize(
            paragraph("Before You Begin", "Heading2"),
            paragraph("OpDiv: Example"),
            paragraph("Opportunity number: TEST"),
            paragraph("The Metadata author: field is set by staff."),
        )
        == {}
    )


def test_leading_cover_lines_receive_cover_position_boundaries():
    body = fromstring(
        '<w:body xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        + "".join((*cover_lines(), *toc_entries()))
        + "</w:body>"
    )
    markers = mark_word_scope(body, source_sha256="0" * 64)
    assert (
        sorted(markers.values()) == ["cover_position"] * 5 + ["table_of_contents"] * 2
    )
