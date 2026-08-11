#!/usr/bin/env python3
"""Verify that a built source distribution contains the release surface."""

from __future__ import annotations

import argparse
import sys
import tarfile
from pathlib import Path, PurePosixPath

FORBIDDEN_PARTS = {
    "calibration",
    "evidence",
    "history",
    "private",
    "research",
}
REQUIRED_FILES = {
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "README.md",
    "SECURITY.md",
    "docs/ARCHITECTURE.md",
    "docs/INTEGRATION_CONTRACT.md",
    "docs/METHODOLOGY.md",
    "docs/PUBLIC_REPOSITORY_BOUNDARY.md",
    "docs/RELEASE_PROCESS.md",
    "docs/consumers/NOFO_BUILDER.md",
    "pyproject.toml",
}


def archive_names(source_distribution: Path) -> set[str]:
    with tarfile.open(source_distribution, mode="r:gz") as archive:
        names: set[str] = set()
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            if len(path.parts) > 1 and member.isfile():
                names.add(PurePosixPath(*path.parts[1:]).as_posix())
        return names


def findings(source_distribution: Path) -> list[str]:
    names = archive_names(source_distribution)
    errors = [
        f"required release file missing: {name}"
        for name in sorted(REQUIRED_FILES.difference(names))
    ]
    for name in sorted(names):
        if FORBIDDEN_PARTS.intersection(PurePosixPath(name).parts):
            errors.append(f"non-release path shipped: {name}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_distribution", type=Path)
    args = parser.parse_args(argv)
    if not args.source_distribution.is_file():
        print(f"ERROR: source distribution does not exist: {args.source_distribution}")
        return 2
    errors = findings(args.source_distribution)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Source-distribution check failed with {len(errors)} error(s).")
        return 1
    print(f"Source-distribution check passed: {args.source_distribution.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
