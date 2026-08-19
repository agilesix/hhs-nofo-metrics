# Contributing

This repository contains the supported HHS NOFO metric package and its public
contracts. A method change can alter reported metrics, so reproducibility and
explicit versioning matter as much as code correctness.

## Development setup

Use Python 3.11 or newer:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pre-commit install
```

Run the local checks with:

```bash
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/pytest --cov=hhs_nofo_metrics --cov-report=term-missing
.venv/bin/python tools/check_public_repo.py
.venv/bin/pre-commit run --all-files
```

To test the distributable artifact:

```bash
.venv/bin/python -m build
.venv/bin/python tools/check_wheel_contents.py dist/*.whl
.venv/bin/python tools/check_sdist_contents.py dist/*.tar.gz
```

CI installs both built distributions into clean environments and runs the
packaged API and CLI as additional smoke tests.

## Method changes

- Never modify a released versioned schema, profile, or method artifact in
  place. Retain it for historical validation and interpretation.
- Give any result-shape change a new schema version. Consumers are required to
  reject schema versions they do not explicitly support.
- Never silently change a released method's arithmetic, selection, tokenizer,
  sentence, character, or syllable behavior.
- Give output-changing behavior a new immutable method version and add focused
  regression tests.
- Preserve released product methods when existing results must remain
  reproducible. Remove superseded, never-released experiments from the release
  repository; Git checkpoints preserve their history.
- Distinguish Microsoft Word calibration evidence from HHS policy decisions.
- Keep draft contracts disconnected from active profiles until they have the
  required approval and validation evidence.
- Record user-visible changes in `CHANGELOG.md`.

## Tests and evidence

Product tests live under `tests/`. The release repository does not contain the
private corpus, desktop automation, or historical research laboratory used
during calibration.

Synthetic fixtures and sanitized aggregate evidence may be committed when
their purpose and expected behavior are documented. Real NOFO PDFs, converted
Word files, screenshots, row-level corpus data, generated reports, and Word
automation workspaces remain outside the public repository.

See [docs/PUBLIC_REPOSITORY_BOUNDARY.md](docs/PUBLIC_REPOSITORY_BOUNDARY.md)
for the complete boundary and run `tools/check_public_repo.py` before every
public release or clean export.

## Microsoft Word calibration

Most development and all ordinary package tests must run without Microsoft
Word. Word automation is reserved for bounded parity questions, uses private
fixtures, and should be announced before it is run because it can disrupt the
desktop session.

## Pull requests

Keep changes focused and describe:

- which method, profile, schema, or tooling contract changed;
- whether outputs can change;
- the evidence and tests supporting the change; and
- any private calibration artifacts intentionally excluded from the commit.
