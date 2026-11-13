import json
from importlib.resources import files

from jsonschema import validate

from hhs_nofo_metrics import SourceBundle, analyze

PROFILE = "hhs-nofo-fy27-word@0.1.0"
PREFIX = "scope_0abcdef012345678"


def test_verified_roles_use_existing_selection_and_emit_only_aggregates():
    html = (
        f'<h1><a id="{PREFIX}_1_s"></a>Cover words<a id="{PREFIX}_1_e"></a></h1>'
        f'<p><a id="{PREFIX}_2_s"></a>Contents 7<a id="{PREFIX}_2_e"></a></p>'
        f'<table><tr><td><p><a id="{PREFIX}_3_s"></a>Writer guidance.'
        f'<a id="{PREFIX}_3_e"></a></p></td></tr></table>'
        '<p class="instruction" role="navigation">Applicants should apply.</p>'
    ).encode()
    source = SourceBundle.from_html(html)
    result = analyze(
        source,
        profile=PROFILE,
        adapter_config={
            "word_boundaries": {
                PREFIX + "_1": "cover_position",
                PREFIX + "_2": "table_of_contents",
                PREFIX + "_3": "instruction",
            }
        },
    ).to_dict()
    assert result["metrics"]["word_count"]["value"] == 3
    assert result["excluded_word_content"] == {
        "cover_position": {"words": 2, "segments": 1},
        "table_of_contents": {"words": 2, "segments": 1},
        "instruction": {"words": 2, "segments": 1},
    }
    assert "Writer guidance" not in json.dumps(result)
    schema = files("hhs_nofo_metrics.schemas").joinpath("analysis-result-1.3.0.json")
    validate(result, json.loads(schema.read_text()))
    old = analyze(source, profile="hhs-nofo-fy27-html@0.6.0").to_dict()
    assert old["metrics"]["word_count"]["value"] == 9
    assert old["schema_version"] == "1.1.0"
    assert "excluded_word_content" not in old


def test_missing_duplicate_or_partial_boundaries_leave_text_countable():
    boundary = PREFIX + "_1"
    for html in (
        f'<p>Keep this<a id="{boundary}_s"></a> and this<a id="{boundary}_e"></a>.</p>',
        f'<p><a id="{boundary}_s"></a>Keep this.</p>',
        f'<p><a id="{boundary}_s"></a>Keep this.<a id="{boundary}_e"></a></p>'
        f'<p><a id="{boundary}_s"></a>Also keep this.</p>',
    ):
        result = analyze(
            SourceBundle.from_html(html.encode()),
            profile=PROFILE,
            adapter_config={"word_boundaries": {boundary: "instruction"}},
        ).to_dict()
        assert result["metrics"]["word_count"]["value"] >= 2
        assert result["excluded_word_content"] == {}
