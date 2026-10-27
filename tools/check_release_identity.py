#!/usr/bin/env python3
"""Check package identity, plus stable release tag/changelog consistency."""

from __future__ import annotations

import argparse
import ast
import re
import sys
import tomllib
from datetime import date
from pathlib import Path

_STABLE_VERSION = r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"


def findings(root: Path, *, tag: str | None = None) -> list[str]:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    tree = ast.parse(
        (root / "src/hhs_nofo_metrics/version.py").read_text(encoding="utf-8")
    )
    fallback = next(
        (
            ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "SOURCE_FALLBACK_VERSION"
            and node.value is not None
        ),
        None,
    )
    errors = []
    if not isinstance(version, str) or re.fullmatch(_STABLE_VERSION, version) is None:
        errors.append("package version must use the stable MAJOR.MINOR.PATCH format")
    if fallback != version:
        errors.append(
            f"source fallback version {fallback!r} differs from package {version!r}"
        )
    if tag is not None:
        if tag != f"v{version}":
            errors.append(f"release tag {tag!r} must match package tag 'v{version}'")
        changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        entries = re.findall(
            rf"^## \[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})$",
            changelog,
            flags=re.MULTILINE,
        )
        if len(entries) != 1:
            errors.append(
                f"release requires one dated changelog heading: "
                f"## [{version}] - YYYY-MM-DD"
            )
        else:
            try:
                date.fromisoformat(entries[0])
            except ValueError:
                errors.append(f"changelog release date {entries[0]!r} is invalid")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--tag", help="Stable release tag to validate, such as v0.6.0")
    args = parser.parse_args(argv)
    try:
        errors = findings(args.root, tag=args.tag)
    except (OSError, KeyError, ValueError, SyntaxError, tomllib.TOMLDecodeError) as exc:
        print(f"ERROR: unable to read release identity: {exc}")
        return 2
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    suffix = f" for {args.tag}" if args.tag is not None else " (untagged development)"
    print(f"Release identity check passed{suffix}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
