"""Command-line interface for supported HHS NOFO Metrics operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from hhs_nofo_metrics.api import (
    analyze,
    inspect_adapter_support,
    list_adapters,
    list_profiles,
    load_profile,
)
from hhs_nofo_metrics.errors import InputError, NofoMetricsError
from hhs_nofo_metrics.serialization import write_json
from hhs_nofo_metrics.sources import SourceArtifact, SourceBundle
from hhs_nofo_metrics.toon_output import encode_toon
from hhs_nofo_metrics.version import PACKAGE_VERSION


class CliUsageError(Exception):
    """The command line does not satisfy a declared command contract."""

    def __init__(self, message: str, *, usage: str) -> None:
        super().__init__(message)
        self.usage = usage


class _ArgumentParser(argparse.ArgumentParser):
    """Emit a compact structured usage error instead of exiting internally."""

    def error(self, message: str) -> None:
        raise CliUsageError(message, usage=self.format_usage().strip())


def _parse_auxiliary_artifacts(values: list[str]) -> tuple[SourceArtifact, ...]:
    artifacts: list[SourceArtifact] = []
    for value in values:
        if "=" not in value:
            raise InputError("--aux must use NAME=PATH syntax")
        name, raw_path = value.split("=", 1)
        path = Path(raw_path).expanduser().resolve()
        kind = path.suffix.casefold().lstrip(".") or "binary"
        try:
            artifacts.append(SourceArtifact(name=name, kind=kind, source=path))
        except ValueError as exc:
            raise InputError(f"Invalid --aux value '{value}': {exc}") from exc
    return tuple(artifacts)


def _source_bundle(
    source: Path,
    auxiliary_values: list[str],
    *,
    source_kind: str = "pdf",
) -> SourceBundle:
    media_type = {"pdf": "application/pdf", "html": "text/html"}[source_kind]
    return SourceBundle(
        primary=SourceArtifact(
            name="primary",
            kind=source_kind,
            source=source,
            media_type=media_type,
        ),
        auxiliaries=_parse_auxiliary_artifacts(auxiliary_values),
    )


def _load_adapter_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    resolved = path.expanduser().resolve()
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"Unable to read adapter configuration: {exc}") from exc
    if not isinstance(payload, dict):
        raise InputError("--adapter-config must contain a JSON object")
    return payload


def _print_data(value: object, *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(value, ensure_ascii=False, sort_keys=True))
        return
    print(encode_toon(value))


def _display_executable() -> str:
    executable = str(Path(sys.argv[0]).expanduser().resolve())
    home = str(Path.home())
    return (
        "~" + executable[len(home) :]
        if executable.startswith(home + "/")
        else executable
    )


def _home_view() -> dict[str, object]:
    adapters = list_adapters()
    return {
        "bin": _display_executable(),
        "description": "Calculate versioned HHS NOFO readability metrics.",
        "profiles": list_profiles(),
        "adapters": [
            {
                "reference": item["reference"],
                "source_kinds": "/".join(item["source_kinds"]),
                "capability_count": len(item["capabilities"]),
            }
            for item in adapters
        ],
        "help": [
            "Run hhs-nofo-metrics profiles show <profile> for metric policy details",
            "Run hhs-nofo-metrics adapters inspect <path> before selecting a PDF adapter",
            "Run hhs-nofo-metrics analyze --help for analysis arguments",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="hhs-nofo-metrics",
        description="Calculate versioned HHS NOFO readability metrics.",
    )
    parser.add_argument(
        "-v",
        "-V",
        "--version",
        action="version",
        version=PACKAGE_VERSION,
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subcommands.add_parser(
        "analyze", help="Analyze one PDF or semantic HTML export"
    )
    analyze_parser.add_argument("source", type=Path)
    analyze_parser.add_argument(
        "--source-kind",
        choices=("pdf", "html"),
        default="pdf",
        help="Primary source type (default: pdf)",
    )
    analyze_parser.add_argument(
        "--profile",
        required=True,
        help="Exact metric profile reference (required)",
    )
    analyze_parser.add_argument(
        "--adapter", help="Override the selected profile's default adapter"
    )
    analyze_parser.add_argument(
        "--aux",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Attach a named auxiliary source artifact",
    )
    analyze_parser.add_argument("--adapter-config", type=Path)
    analyze_parser.add_argument("--production-path", default="unknown")
    analyze_parser.add_argument("--document-id")
    analyze_parser.add_argument("--revision")
    analyze_parser.add_argument("--output", type=Path, required=True)

    profiles_parser = subcommands.add_parser("profiles", help="Inspect profiles")
    profiles_commands = profiles_parser.add_subparsers(
        dest="profiles_command", required=True
    )
    profiles_commands.add_parser("list", help="List packaged profile references")
    profile_show = profiles_commands.add_parser("show", help="Show one profile")
    profile_show.add_argument("reference")

    adapters_parser = subcommands.add_parser(
        "adapters", help="Inspect installed extraction adapters"
    )
    adapters_commands = adapters_parser.add_subparsers(
        dest="adapters_command", required=True
    )
    adapters_commands.add_parser("list", help="List installed adapters")
    adapter_show = adapters_commands.add_parser("show", help="Show one adapter")
    adapter_show.add_argument("reference")
    adapter_inspect = adapters_commands.add_parser(
        "inspect", help="Report source support without running analysis"
    )
    adapter_inspect.add_argument("source", type=Path)
    adapter_inspect.add_argument(
        "--source-kind", choices=("pdf", "html"), default="pdf"
    )
    adapter_inspect.add_argument("--adapter")
    adapter_inspect.add_argument(
        "--aux", action="append", default=[], metavar="NAME=PATH"
    )
    return parser


def _run_adapters(args: argparse.Namespace, *, json_output: bool) -> int:
    adapters = list_adapters()
    if args.adapters_command == "list":
        payload: dict[str, object]
        if json_output:
            payload = {"count": len(adapters), "adapters": adapters}
        else:
            payload = {
                "count": len(adapters),
                "adapters": [
                    {
                        "reference": item["reference"],
                        "source_kinds": "/".join(item["source_kinds"]),
                        "capability_count": len(item["capabilities"]),
                    }
                    for item in adapters
                ],
                "help": [
                    "Run hhs-nofo-metrics adapters show <adapter> for details",
                    "Run hhs-nofo-metrics adapters inspect <path> to inspect source support",
                ],
            }
        _print_data(payload, json_output=json_output)
        return 0
    if args.adapters_command == "show":
        exact = [
            item
            for item in adapters
            if item["reference"] == args.reference or item["id"] == args.reference
        ]
        if not exact:
            raise InputError(f"Unknown adapter: {args.reference}")
        if len(exact) > 1:
            raise InputError(
                f"Ambiguous adapter reference: {args.reference}; use id@version"
            )
        _print_data(exact[0], json_output=json_output)
        return 0
    assessments = inspect_adapter_support(
        _source_bundle(
            args.source,
            args.aux,
            source_kind=args.source_kind,
        ),
        adapter=args.adapter,
    )
    _print_data(
        {
            "source_kind": args.source_kind,
            "assessment_count": len(assessments),
            "assessments": assessments,
            "selection_performed": False,
        },
        json_output=json_output,
    )
    return 0


def run(args: argparse.Namespace, *, json_output: bool = False) -> int:
    if args.command == "profiles":
        if args.profiles_command == "list":
            profiles = list_profiles()
            payload: dict[str, object] = {"count": len(profiles), "profiles": profiles}
            if not json_output:
                payload["help"] = [
                    "Run hhs-nofo-metrics profiles show <profile> for details"
                ]
            _print_data(payload, json_output=json_output)
        else:
            _print_data(load_profile(args.reference).to_dict(), json_output=json_output)
        return 0
    if args.command == "adapters":
        return _run_adapters(args, json_output=json_output)

    result = analyze(
        _source_bundle(
            args.source,
            args.aux,
            source_kind=args.source_kind,
        ),
        adapter=args.adapter,
        adapter_config=_load_adapter_config(args.adapter_config),
        profile=args.profile,
        production_path=args.production_path,
        document_id=args.document_id,
        revision=args.revision,
    )
    output = write_json(args.output, result)
    _print_data(
        {
            "status": "ok",
            "output": str(output),
            "source_sha256": result.source.sha256,
            "profile": f"{result.profile.id}@{result.profile.version}",
        },
        json_output=json_output,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    json_output = False
    if "--json" in values:
        if values.count("--json") > 1:
            _print_data(
                {
                    "error": {
                        "code": "usage_error",
                        "message": "--json may be supplied only once",
                        "usage": "hhs-nofo-metrics [--json] <command> ...",
                    }
                },
                json_output=False,
            )
            return 2
        values.remove("--json")
        json_output = True
    if not values:
        _print_data(_home_view(), json_output=json_output)
        return 0
    try:
        return run(build_parser().parse_args(values), json_output=json_output)
    except CliUsageError as exc:
        _print_data(
            {
                "error": {
                    "code": "usage_error",
                    "message": str(exc),
                    "usage": exc.usage,
                    "help": "Use one of: analyze, profiles, adapters, --help, --version.",
                }
            },
            json_output=json_output,
        )
        return 2
    except NofoMetricsError as exc:
        _print_data({"error": exc.to_dict()}, json_output=json_output)
        return 1
    except OSError as exc:
        _print_data(
            {
                "error": {
                    "code": "io_error",
                    "message": str(exc),
                }
            },
            json_output=json_output,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
