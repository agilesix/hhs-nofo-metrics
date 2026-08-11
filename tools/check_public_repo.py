#!/usr/bin/env python3
"""Fail when the prospective public tree contains common private artifacts."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

MAX_TRACKED_BYTES = 2 * 1024 * 1024
FORBIDDEN_PARTS = {
    ".agentstate",
    ".agentstate-lite",
    ".venv",
    "__pycache__",
    "build",
    "corpus",
    "corpora",
    "debug-artifacts",
    "dist",
    "evaluation-data",
    "htmlcov",
    "private",
    "private-research",
    "word-automation-workspace",
}
LOCAL_MARKERS = (
    "/" + "Users/",
    "/" + "home/",
    "C:" + "\\Users\\",
    "NOFO_" + "PDF_Evaluation_Data",
)
REVIEW_BINARY_SUFFIXES = {
    ".doc",
    ".docx",
    ".jpg",
    ".jpeg",
    ".odt",
    ".pdf",
    ".png",
    ".pptx",
    ".tif",
    ".tiff",
    ".xls",
    ".xlsx",
}


def prospective_files(root: Path) -> list[Path]:
    completed = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [
        root / value.decode("utf-8") for value in completed.stdout.split(b"\0") if value
    ]


def history_findings(root: Path) -> list[str]:
    findings: list[str] = []
    for marker in LOCAL_MARKERS:
        completed = subprocess.run(
            [
                "git",
                "log",
                "--all",
                "--format=%H",
                "--fixed-strings",
                f"-S{marker}",
                "--",
                ".",
            ],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        commits = sorted(set(completed.stdout.split()))
        if commits:
            findings.append(
                f"local/private marker {marker!r} appears in Git history: "
                + ", ".join(value[:12] for value in commits)
            )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--history",
        action="store_true",
        help="also fail when local/private markers appear anywhere in Git history",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []
    warnings: list[str] = []
    files = prospective_files(root)
    for path in files:
        relative = path.relative_to(root)
        folded_parts = {part.casefold() for part in relative.parts}
        forbidden = folded_parts.intersection(FORBIDDEN_PARTS)
        if forbidden:
            errors.append(
                f"forbidden private/generated path component {sorted(forbidden)!r}: {relative}"
            )
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > MAX_TRACKED_BYTES:
            errors.append(
                f"file exceeds {MAX_TRACKED_BYTES} bytes: {relative} ({size})"
            )
        if path.suffix.casefold() in REVIEW_BINARY_SUFFIXES:
            warnings.append(
                f"manually review binary artifact before publication: {relative}"
            )
        data = path.read_bytes()
        if b"\0" in data:
            continue
        text = data.decode("utf-8", errors="replace")
        for marker in LOCAL_MARKERS:
            if marker in text:
                errors.append(f"local/private marker {marker!r}: {relative}")

    if args.history:
        errors.extend(history_findings(root))

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Public repository check failed with {len(errors)} error(s).")
        return 1
    print(
        f"Public repository check passed for {len(files)} prospective tracked file(s)"
        + (" and Git history" if args.history else "")
        + (f" with {len(warnings)} warning(s)." if warnings else ".")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
