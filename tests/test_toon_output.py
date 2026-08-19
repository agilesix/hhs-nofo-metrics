from __future__ import annotations

import math

import pytest

from hhs_nofo_metrics.toon_output import encode_toon


def test_encodes_object_with_inline_array_and_tabular_rows() -> None:
    payload = {
        "count": 2,
        "profiles": ["profile-a@1", "profile-b@1"],
        "adapters": [
            {"reference": "pdf@1", "source_kinds": "pdf", "capability_count": 4},
            {"reference": "html@1", "source_kinds": "html", "capability_count": 3},
        ],
    }

    assert encode_toon(payload) == (
        "count: 2\n"
        "profiles[2]: profile-a@1,profile-b@1\n"
        "adapters[2]{reference,source_kinds,capability_count}:\n"
        "  pdf@1,pdf,4\n"
        "  html@1,html,3"
    )


def test_quotes_ambiguous_strings_and_escapes_controls() -> None:
    payload = {
        "empty": "",
        "numeric": "1",
        "boolean": "true",
        "punctuation": "one,two: three",
        "line": "one\ntwo",
    }

    assert encode_toon(payload) == (
        'empty: ""\n'
        'numeric: "1"\n'
        'boolean: "true"\n'
        'punctuation: "one,two: three"\n'
        'line: "one\\ntwo"'
    )


def test_encodes_nested_mixed_content() -> None:
    payload = {
        "assessment_count": 1,
        "assessments": [
            {
                "adapter": {"id": "pdf", "version": "1"},
                "assessment": {
                    "status": "supported",
                    "reasons": ["one", "two"],
                },
            }
        ],
        "selection_performed": False,
    }

    assert encode_toon(payload) == (
        "assessment_count: 1\n"
        "assessments[1]:\n"
        "  - adapter:\n"
        "      id: pdf\n"
        '      version: "1"\n'
        "    assessment:\n"
        "      status: supported\n"
        "      reasons[2]: one,two\n"
        "selection_performed: false"
    )


def test_encodes_keyed_tabular_object() -> None:
    assert encode_toon(
        {
            "first": {"status": "ok", "count": 2},
            "second": {"status": "review", "count": 3},
        }
    ) == ("[2:]{status,count}:\n  first: ok,2\n  second: review,3")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "null"),
        (True, "true"),
        (False, "false"),
        (0, "0"),
        (12.5, "12.5"),
        (math.inf, "null"),
        (-math.inf, "null"),
        (math.nan, "null"),
        (1e-7, "1e-7"),
        (1e21, "1e+21"),
        ([], "[]"),
        ([1, "two", False], "[3]: 1,two,false"),
    ],
)
def test_encodes_primitive_and_compact_root_values(
    value: object, expected: str
) -> None:
    assert encode_toon(value) == expected  # type: ignore[arg-type]


def test_encodes_empty_and_nested_nonuniform_list_items() -> None:
    value = {
        "items": [
            {},
            [],
            [1, 2],
            {"name": "first", "details": {"active": True}},
        ]
    }

    assert encode_toon(value) == (
        "items[4]:\n"
        "  -\n"
        "  - [0]:\n"
        "  - [2]: 1,2\n"
        "  - name: first\n"
        "    details:\n"
        "      active: true"
    )


def test_rejects_non_json_values_and_unpaired_surrogates() -> None:
    with pytest.raises(TypeError, match="Unsupported TOON root: set"):
        encode_toon({"not", "json"})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Unsupported TOON value: set"):
        encode_toon({"value": {1, 2}})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="Unsupported TOON list item: set"):
        encode_toon([{"valid": True}, {1, 2}])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="unpaired Unicode surrogate"):
        encode_toon("\ud800")
