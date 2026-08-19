from __future__ import annotations

import os
from pathlib import Path

import pytest

from hhs_nofo_metrics.serialization import write_json


def test_write_json_atomically_replaces_existing_file(tmp_path: Path) -> None:
    output = tmp_path / "result.json"
    output.write_text("old\n", encoding="utf-8")

    assert write_json(output, {"status": "new"}) == output

    assert output.read_text(encoding="utf-8") == '{\n  "status": "new"\n}\n'
    assert not list(tmp_path.glob(".result.json.*.tmp"))


def test_write_json_preserves_existing_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "result.json"
    output.write_text("old\n", encoding="utf-8")

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        write_json(output, {"status": "new"})

    assert output.read_text(encoding="utf-8") == "old\n"
    assert not list(tmp_path.glob(".result.json.*.tmp"))
