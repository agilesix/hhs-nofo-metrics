# Release process

This checklist separates public package verification from private evidence.
Source documents and row-level calibration data never enter this repository.

## Package gate

1. Confirm the changelog and package version describe the same release.
2. Run formatting, lint, tests, coverage, and pre-commit checks.
3. Run `tools/check_public_repo.py --history`.
4. Build the wheel and source distribution.
5. Run both distribution-boundary checks and install each artifact in a clean
   environment.
6. Confirm the CLI default is TOON 4.1, `--json` is valid JSON, and the Python
   API exports `AnalysisResult`.

## Private real-document gate

Before designating a release for integration, evaluate a frozen private cohort
containing at least:

- one semantic Builder HTML export;
- one native Builder/Prince tagged PDF;
- one Builder Word-to-PDF export;
- one non-Builder tagged PDF; and
- one untagged or structurally degraded PDF.

Store the receipt outside Git. The receipt should contain only the package
commit, profile references, a cohort-manifest hash, document counts, result and
reliability distributions, unexpected-error counts, and the reviewer/date. It
must not contain filenames, paths, extracted text, source metadata, or
document-level records.

The gate passes when every input returns either a schema-valid result or a
documented typed error, no source text or local path crosses the result
boundary, tagged blank pages do not count as extraction failures, and each
source follows its intended analysis path.

## Public-release gate

Before making the repository or a distribution public, choose and add the
project license. Do not infer a license from dependencies or organizational
affiliation. Re-run the history and secret scans after the final commit and
publish from a clean export if any private material ever entered Git history.
