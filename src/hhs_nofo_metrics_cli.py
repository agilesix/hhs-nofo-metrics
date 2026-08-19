"""Fast console entry point that avoids loading PDF dependencies for version probes."""

from __future__ import annotations

import sys
from importlib import metadata

PACKAGE_NAME = "hhs-nofo-metrics"
VERSION_FLAGS = frozenset({"-v", "-V", "--version"})


def _installed_version() -> str:
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        from hhs_nofo_metrics.version import PACKAGE_VERSION

        return PACKAGE_VERSION


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if len(values) == 1 and values[0] in VERSION_FLAGS:
        print(_installed_version())
        return 0
    from hhs_nofo_metrics.cli import main as full_main

    return full_main(values)


if __name__ == "__main__":
    raise SystemExit(main())
