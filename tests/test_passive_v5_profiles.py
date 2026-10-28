"""Synthetic end-to-end checks for opt-in definition-modifier profiles."""

import json

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)

from hhs_nofo_metrics import SourceBundle, analyze, load_profile
from hhs_nofo_metrics.profile_store import load_profile_record

PAIRS = [
    ("hhs-nofo-fy27-html@0.5.0", "hhs-nofo-fy27-html@0.6.0"),
    ("hhs-nofo-fy27-pdf-estimate@0.6.0", "hhs-nofo-fy27-pdf-estimate@0.7.0"),
    (
        "hhs-nofo-fy27-generic-pdf-estimate@0.5.0",
        "hhs-nofo-fy27-generic-pdf-estimate@0.6.0",
    ),
]
TEXTS = (
    "An eligible entity as defined by the charter.",
    "Applications are reviewed by the board.",
    "An entity as defined by the charter is selected.",
    "Applicants submit forms.",
)


@pytest.mark.parametrize("old_ref,new_ref", PAIRS)
def test_profile_changes_only_identity_description_and_passive_method(old_ref, new_ref):
    old, old_hash = load_profile_record(old_ref)
    new, new_hash = load_profile_record(new_ref)
    old_data, new_data = old.to_dict(), new.to_dict()
    assert old_hash != new_hash
    for key in ("profile_version", "description"):
        old_data.pop(key)
        new_data.pop(key)
    old_data["methods"]["passive_classifier"]["version"] = "0.5.0-provisional"
    assert old_data == new_data


def _pdf_source(path, tagged):
    writer = PdfWriter()
    # A blank cover keeps all invented body lines out of generic cover rules.
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
    stream = DecodedStreamObject()
    stream.set_data(
        "\n".join(
            f"/P <</MCID {i}>> BDC BT /F1 10 Tf 72 {700 - i * 28} Td ({text}) Tj ET EMC"
            for i, text in enumerate(TEXTS)
        ).encode()
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
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
                for i in range(len(TEXTS))
            ]
        )
        writer.root_object[NameObject("/StructTreeRoot")] = root_ref
    writer.write(path)
    return path


@pytest.mark.parametrize(
    "kind,pair", [("html", PAIRS[0]), ("tagged", PAIRS[1]), ("generic", PAIRS[2])]
)
def test_public_analysis_selects_v5_and_preserves_other_metrics(tmp_path, kind, pair):
    if kind == "html":
        source = SourceBundle.from_html(
            (
                "<main>" + "".join(f"<p>{text}</p>" for text in TEXTS) + "</main>"
            ).encode()
        )
    else:
        source = _pdf_source(tmp_path / "invented.pdf", tagged=kind == "tagged")
    old, new = (analyze(source, profile=reference) for reference in pair)
    old_passive = old.metrics["passive_sentence_percentage"]
    new_passive = new.metrics["passive_sentence_percentage"]
    # Four independent source sentences: modifier alone, finite passive,
    # modifier plus finite passive, and active. Only the first changes.
    assert old_passive.components["sentence_count"] == 4
    assert new_passive.components["sentence_count"] == 4
    assert old_passive.components["passive_sentence_count"] == 3
    assert new_passive.components["passive_sentence_count"] == 2
    assert old_passive.value == 75
    assert new_passive.value == 50
    assert new_passive.method.version == "0.5.0-provisional"
    for key in old.metrics:
        if key != "passive_sentence_percentage":
            assert old.metrics[key].to_dict() == new.metrics[key].to_dict()
    # The serialization contract must still be source-free.
    output = json.dumps(new.to_dict())
    assert all(text not in output for text in TEXTS)
    assert str(tmp_path) not in output
    assert load_profile(pair[1]).reference == pair[1]
