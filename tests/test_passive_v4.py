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
from hhs_nofo_metrics.methods import passive_voice as legacy
from hhs_nofo_metrics.methods import passive_voice_v4 as corrected
from hhs_nofo_metrics.profile_store import load_profile_record


@pytest.mark.parametrize("apostrophe", ["'", "’"])
@pytest.mark.parametrize(
    "text",
    [
        "Applications aren't accepted after Friday.",
        "The application wasn't reviewed by the agency.",
        "Costs weren't approved.",
        "The application isn't required.",
        "You're required to submit forms.",
        "We're selected by the agency.",
        "They're indeed approved.",
        "I'm being reviewed by experts.",
        "It's being reviewed by the agency.",
        "It's been approved.",
        "Applications haven't been approved.",
    ],
)
def test_contracted_passives(text, apostrophe):
    assert corrected.classify_passive_sentence(text.replace("'", apostrophe)).is_passive


@pytest.mark.parametrize(
    "text",
    [
        "The program is in need of additional staff.",
        "The applicant is indeed eligible.",
        "Applicants aren't eligible.",
        "The program wasn't ready.",
        "He's reviewed the applications.",
        "It's required extensive coordination.",
        "It's required extensive coordination by the team.",
        "The agency's approved plan is available.",
        "It's approved.",  # ambiguous is/has; deliberately retain no match
        "He's required; by Friday the team will finish.",
        "He's replied by email.",
        "She's traveled by train.",
        "She's volunteered by signing up online.",
        "She's arrived by train.",
        "He's paid by card.",
        "It's required, by my estimate, two hours of work.",
        "He's required by email that applicants submit forms.",
        "They're prepared to submit.",
        "There are proposed subawards.",
        "There is no set limit.",
        "The officers are involved in implementation.",
        "The deadline has passed.",
    ],
)
def test_active_and_ambiguous_controls(text):
    assert not corrected.classify_passive_sentence(text).is_passive


@pytest.mark.parametrize(
    "text",
    [
        "The application is indeed required by the agency.",
        "Applications are reviewed by experts.",
        "The award will be made in September.",
        "Applicants may get selected for an interview.",
        "Use the method as defined by statute.",
    ],
)
def test_preserved_and_modifier_passives(text):
    assert corrected.classify_passive_sentence(text).is_passive


def test_released_method_remains_reproducible():
    assert not legacy.classify_passive_sentence(
        "Applications aren't accepted."
    ).is_passive
    assert legacy.classify_passive_sentence(
        "The applicant is indeed eligible."
    ).is_passive
    assert legacy.METHOD_VERSION == "0.3.0-provisional"


def test_ambiguous_is_has_contraction_remains_an_explicit_limitation():
    # Do not infer is from 's: an active perfect can also have a by-phrase.
    assert not corrected.classify_passive_sentence(
        "It's required by the agency."
    ).is_passive


def test_percentage_changes_with_same_sentences_and_other_metrics():
    html = b"""<main id="download_target">
      <p>Applications aren't accepted after Friday.</p>
      <p>The application wasn't reviewed by the agency.</p>
      <p>Applications aren't evaluated by the agency.</p>
      <p>The program is in need of additional staff.</p>
      <p>The applicant is indeed eligible.</p>
    </main>"""
    source = SourceBundle.from_html(html)
    old = analyze(
        source,
        profile="hhs-nofo-fy27-html@0.4.0",
        adapter_config={"root_id": "download_target"},
    )
    new = analyze(
        source,
        profile="hhs-nofo-fy27-html@0.5.0",
        adapter_config={"root_id": "download_target"},
    )
    for result, percentage, passive_count in [(old, 40, 2), (new, 60, 3)]:
        metric = result.metrics["passive_sentence_percentage"]
        assert metric.value == percentage
        assert metric.components["sentence_count"] == 5
        assert metric.components["passive_sentence_count"] == passive_count
    assert (
        new.metrics["passive_sentence_percentage"].method.version == "0.4.0-provisional"
    )
    for key in old.metrics:
        if key != "passive_sentence_percentage":
            assert old.metrics[key].to_dict() == new.metrics[key].to_dict()
    assert (
        corrected.count_passive_sentences(
            ("Applications aren't accepted and aren't reviewed.",)
        )
        == 1
    )


@pytest.mark.parametrize(
    "reference",
    [
        "hhs-nofo-fy27-html@0.5.0",
        "hhs-nofo-fy27-pdf-estimate@0.6.0",
        "hhs-nofo-fy27-generic-pdf-estimate@0.5.0",
    ],
)
def test_corrected_profile_identity(reference):
    profile, _ = load_profile_record(reference)
    assert profile.methods["passive_classifier"].version == "0.4.0-provisional"


@pytest.mark.parametrize("tagged", [True, False])
def test_pdf_paths_select_corrected_method_without_changing_denominator(
    tmp_path, tagged
):
    texts = [
        "Applications aren't accepted after Friday.",
        "The application wasn't reviewed by the agency.",
        "Applications aren't evaluated by the agency.",
        "The program is in need of additional staff.",
        "The applicant is indeed eligible.",
    ]
    writer = PdfWriter()
    # Generic PDF cover-position rules deliberately exclude the first four
    # lines on page one. Put the controlled body on page two for both paths.
    writer.add_blank_page(width=612, height=792)
    page = writer.add_blank_page(width=612, height=792)
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    content = DecodedStreamObject()
    content.set_data(
        "\n".join(
            f"/P <</MCID {i}>> BDC BT /F1 12 Tf 72 {700 - i * 24} Td ({text}) Tj ET EMC"
            for i, text in enumerate(texts)
        ).encode()
    )
    page[NameObject("/Contents")] = writer._add_object(content)
    if tagged:
        root = DictionaryObject({NameObject("/Type"): NameObject("/StructTreeRoot")})
        root_ref = writer._add_object(root)
        root[NameObject("/K")] = ArrayObject(
            [
                writer._add_object(
                    DictionaryObject(
                        {
                            NameObject("/Type"): NameObject("/StructElem"),
                            NameObject("/S"): NameObject("/P"),
                            NameObject("/P"): root_ref,
                            NameObject("/Pg"): page.indirect_reference,
                            NameObject("/K"): NumberObject(i),
                        }
                    )
                )
                for i in range(len(texts))
            ]
        )
        writer.root_object[NameObject("/StructTreeRoot")] = root_ref
    path = tmp_path / "synthetic.pdf"
    writer.write(path)
    old_ref = (
        "hhs-nofo-fy27-pdf-estimate@0.5.0"
        if tagged
        else "hhs-nofo-fy27-generic-pdf-estimate@0.4.0"
    )
    new_ref = (
        "hhs-nofo-fy27-pdf-estimate@0.6.0"
        if tagged
        else "hhs-nofo-fy27-generic-pdf-estimate@0.5.0"
    )
    old, new = analyze(path, profile=old_ref), analyze(path, profile=new_ref)
    for result, expected in [(old, 40), (new, 60)]:
        passive = result.metrics["passive_sentence_percentage"]
        assert passive.value == expected
        assert passive.components["sentence_count"] == 5
    assert (
        new.metrics["passive_sentence_percentage"].method.version == "0.4.0-provisional"
    )
    for key in old.metrics:
        if key != "passive_sentence_percentage":
            assert old.metrics[key].to_dict() == new.metrics[key].to_dict()
