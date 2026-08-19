#!/usr/bin/env python3
"""Verify that a built wheel contains the supported release surface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

FORBIDDEN_PARTS = {
    "calibration",
    "evidence",
    "history",
    "research",
}
REQUIRED_FILES = {
    "hhs_nofo_metrics_cli.py",
    "hhs_nofo_metrics/profiles/hhs-nofo-fy27-generic-pdf-estimate-0.4.0.json",
    "hhs_nofo_metrics/profiles/hhs-nofo-fy27-html-0.4.0.json",
    "hhs_nofo_metrics/profiles/hhs-nofo-fy27-pdf-estimate-0.5.0.json",
    "hhs_nofo_metrics/schemas/analysis-result-1.1.0.json",
    "hhs_nofo_metrics/schemas/analysis-result-1.2.0.json",
    "hhs_nofo_metrics/schemas/profile-1.1.0.json",
}


def findings(wheel: Path) -> list[str]:
    errors: list[str] = []
    with ZipFile(wheel) as archive:
        names = sorted(name for name in archive.namelist() if not name.endswith("/"))
    missing = sorted(REQUIRED_FILES.difference(names))
    errors.extend(f"required release file missing: {name}" for name in missing)
    for name in names:
        path = PurePosixPath(name)
        if FORBIDDEN_PARTS.intersection(path.parts):
            errors.append(f"non-release path shipped: {name}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args(argv)
    if not args.wheel.is_file():
        print(f"ERROR: wheel does not exist: {args.wheel}")
        return 2
    errors = findings(args.wheel)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Wheel boundary check failed with {len(errors)} error(s).")
        return 1
    print(f"Wheel boundary check passed: {args.wheel.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
