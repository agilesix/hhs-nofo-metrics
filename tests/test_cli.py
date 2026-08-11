from __future__ import annotations

import json
from pathlib import Path

import pytest
from pypdf import PdfWriter

import hhs_nofo_metrics.cli as cli


def write_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with path.open("wb") as stream:
        writer.write(stream)


def json_stdout(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    return json.loads(captured.out)


def test_home_and_profile_commands_expose_compact_public_contracts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main([]) == 0
    home = capsys.readouterr()
    assert home.err == ""
    assert "description: Calculate versioned HHS NOFO readability metrics." in home.out
    assert "profiles[3]:" in home.out
    assert "adapters[3]{reference,source_kinds,capability_count}:" in home.out

    assert cli.main(["profiles", "list", "--json"]) == 0
    listed = json_stdout(capsys)
    assert listed["count"] == 3
    assert "help" not in listed

    assert cli.main(["profiles", "show", "hhs-nofo-fy27-html@0.4.0", "--json"]) == 0
    shown = json_stdout(capsys)
    assert shown["profile_id"] == "hhs-nofo-fy27-html"
    assert shown["profile_version"] == "0.4.0"


def test_adapter_commands_list_show_inspect_and_reject_unknown_adapter(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "fixture.pdf"
    write_pdf(source)

    assert cli.main(["adapters", "list"]) == 0
    listed = capsys.readouterr()
    assert listed.err == ""
    assert "count: 3" in listed.out
    assert "help[2]:" in listed.out

    assert cli.main(["adapters", "show", "hhs-pdf-adapter", "--json"]) == 0
    shown = json_stdout(capsys)
    assert shown["reference"] == "hhs-pdf-adapter@0.4.0"

    assert (
        cli.main(
            [
                "adapters",
                "inspect",
                str(source),
                "--adapter",
                "pdf",
                "--json",
            ]
        )
        == 0
    )
    inspected = json_stdout(capsys)
    assert inspected["selection_performed"] is False
    assert inspected["assessment_count"] == 1
    assert inspected["assessments"][0]["assessment"]["status"] == "supported"

    assert cli.main(["adapters", "show", "missing", "--json"]) == 1
    error = json_stdout(capsys)["error"]
    assert error["code"] == "input_error"
    assert error["message"] == "Unknown adapter: missing"


def test_adapter_show_requires_an_exact_version_when_an_id_is_ambiguous(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "list_adapters",
        lambda: [
            {
                "id": "shared",
                "version": "1.0.0",
                "reference": "shared@1.0.0",
                "source_kinds": ["pdf"],
                "capabilities": ["text"],
            },
            {
                "id": "shared",
                "version": "2.0.0",
                "reference": "shared@2.0.0",
                "source_kinds": ["pdf"],
                "capabilities": ["text"],
            },
        ],
    )

    assert cli.main(["adapters", "show", "shared", "--json"]) == 1
    error = json_stdout(capsys)["error"]
    assert error["code"] == "input_error"
    assert "Ambiguous adapter reference" in error["message"]


def test_analyze_html_writes_result_and_machine_readable_receipt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "export.html"
    config = tmp_path / "adapter.json"
    output = tmp_path / "result.json"
    source.write_text(
        '<main id="download_target"><h1>Apply now</h1>'
        "<p>Applications are reviewed.</p></main>",
        encoding="utf-8",
    )
    config.write_text('{"root_id":"download_target"}', encoding="utf-8")

    assert (
        cli.main(
            [
                "analyze",
                str(source),
                "--source-kind",
                "html",
                "--profile",
                "hhs-nofo-fy27-html@0.4.0",
                "--adapter-config",
                str(config),
                "--production-path",
                "test_export_html",
                "--document-id",
                "notice-1",
                "--revision",
                "revision-2",
                "--output",
                str(output),
                "--json",
            ]
        )
        == 0
    )

    receipt = json_stdout(capsys)
    assert receipt["status"] == "ok"
    assert receipt["output"] == str(output.resolve())
    assert receipt["profile"] == "hhs-nofo-fy27-html@0.4.0"
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["source"]["document_id"] == "notice-1"
    assert result["source"]["revision"] == "revision-2"
    assert result["metrics"]["passive_sentence_percentage"]["value"] == 100


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("not json", "Unable to read adapter configuration"),
        ("[]", "--adapter-config must contain a JSON object"),
    ],
)
def test_adapter_configuration_errors_are_stable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    contents: str,
    message: str,
) -> None:
    source = tmp_path / "export.html"
    config = tmp_path / "adapter.json"
    output = tmp_path / "result.json"
    source.write_text("<main><p>Apply now.</p></main>", encoding="utf-8")
    config.write_text(contents, encoding="utf-8")

    assert (
        cli.main(
            [
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
                "--json",
            ]
        )
        == 1
    )
    error = json_stdout(capsys)["error"]
    assert error["code"] == "input_error"
    assert message in error["message"]
    assert not output.exists()


@pytest.mark.parametrize(
    ("auxiliary", "message"),
    [
        ("manifest.json", "--aux must use NAME=PATH syntax"),
        ("Bad-Name=manifest.json", "Invalid --aux value"),
    ],
)
def test_auxiliary_argument_errors_are_structured(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    auxiliary: str,
    message: str,
) -> None:
    source = tmp_path / "fixture.pdf"
    write_pdf(source)

    assert (
        cli.main(
            [
                "adapters",
                "inspect",
                str(source),
                "--aux",
                auxiliary,
                "--json",
            ]
        )
        == 1
    )
    error = json_stdout(capsys)["error"]
    assert error["code"] == "input_error"
    assert message in error["message"]


def test_usage_and_io_failures_have_distinct_exit_codes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["profiles", "list", "--json", "--json"]) == 2
    duplicate = capsys.readouterr()
    assert duplicate.err == ""
    assert "code: usage_error" in duplicate.out
    assert "--json may be supplied only once" in duplicate.out

    assert cli.main(["unknown", "--json"]) == 2
    usage = json_stdout(capsys)["error"]
    assert usage["code"] == "usage_error"
    assert "invalid choice" in usage["message"]
    assert "usage" in usage
    assert "help" in usage

    def fail_with_os_error(*args: object, **kwargs: object) -> int:
        raise OSError("disk unavailable")

    monkeypatch.setattr(cli, "run", fail_with_os_error)
    assert cli.main(["profiles", "list", "--json"]) == 1
    io_error = json_stdout(capsys)["error"]
    assert io_error == {"code": "io_error", "message": "disk unavailable"}


def test_json_only_home_view_and_executable_path_collapsing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    executable = Path.home() / ".local/bin/hhs-nofo-metrics"
    monkeypatch.setattr(cli.sys, "argv", [str(executable)])

    assert cli.main(["--json"]) == 0
    home = json_stdout(capsys)
    assert home["bin"] == "~/.local/bin/hhs-nofo-metrics"
    assert len(home["profiles"]) == 3
