# Repository guidance for agents

## Start here

Read [README.md](README.md), [CONTRIBUTING.md](CONTRIBUTING.md), and the relevant
contract before editing behavior. [docs/README.md](docs/README.md) maps the
available documentation. Check the working tree and preserve existing work.

This package calculates deterministic NOFO metrics and provenance. Consumers
own orchestration, persistence, permissions, UI, thresholds, and clearance
interpretation. Keep those responsibilities outside the package.

## Code map

- `src/hhs_nofo_metrics/api.py`: public analysis and inspection entry points.
- `adapters/`: HTML, tagged PDF, generic PDF, and adapter contracts.
- `metric_scopes.py`, `resolved_scope.py`, `semantic_html_engine.py`: selection,
  resolved counts, and metric orchestration.
- `methods/`: independently versioned token, sentence, syllable, passive, and
  readability behavior.
- `profiles/`, `schemas/`, `models/`: packaged policy and result contracts.
- `src/hhs_nofo_metrics/cli.py`: CLI; `src/hhs_nofo_metrics_cli.py`: launcher.
- `tests/`: product regressions and synthetic fixtures.
- `tools/`: repository and distribution boundary checks.

Paths above are relative to `src/hhs_nofo_metrics/` unless explicitly prefixed.

## Measurement changes

- Reproduce reported behavior against the relevant current package before
  treating historical observations as a present failure.
- Check extraction, ordering, block boundaries, selection, and denominators
  separately from formulas. Do not change formulas to hide extraction errors.
- Keep document Word Count separate from readability-sentence scope. All
  sentence-based metrics must share the accepted sentence inventory.
- Preserve released profile, schema, and method artifacts. Output-changing
  behavior needs an explicit new identity at the layer that changed, focused
  regressions, and a changelog entry. Retain historical profiles and methods
  needed to reproduce old results.
- For adapter changes, update adapter and resolver identities as applicable;
  record which package consumers need. Package identity is declared in
  `pyproject.toml` and the fallback in `version.py`; align CI smoke expectations.
  Run `tools/check_release_identity.py` for consistency; release tags additionally
  need a matching dated changelog entry. See the release process before tagging.
- A successful analysis is not evidence that its extraction or scores are
  correct. For extraction fixes, use a small synthetic fixture with independently
  enumerated text, boundaries, counts, and metric expectations.
- Keep built-in results source-free. Preserve status, uncertainty, reliability,
  and provenance; never turn an unavailable value into zero or an overall pass.

## Development and verification

Use Python 3.11 or newer and the repository's `.venv`. Setup and the complete
check commands are in [CONTRIBUTING.md](CONTRIBUTING.md).

For behavior changes, run focused regressions, formatting, lint, the full test
suite with coverage, pre-commit, and the public-boundary check. For packaging
or release changes, also build both distributions, check their contents, and
verify clean-install API/CLI behavior as described in
[the release process](docs/RELEASE_PROCESS.md). For documentation-only changes,
check links, command accuracy, formatting, and the public boundary; do not add
implementation-mirroring tests.

`pre-commit run --all-files` checks tracked files. Include new files explicitly
with `pre-commit run --files <paths>` until they are tracked.

## Evidence and delivery

Follow [the public boundary](docs/PUBLIC_REPOSITORY_BOUNDARY.md). Private PDFs,
Word conversions, screenshots, per-document reports, local paths, credentials,
and generated release artifacts stay outside Git. Commit synthetic fixture
generators and sanitized aggregate evidence with documented expectations.

Routine development must run without Microsoft Word. Announce any bounded Word
automation before running it because it can disrupt the desktop. If an actual
export or private cohort is unavailable, say so and keep its validation pending;
do not describe synthetic evidence as Word parity or HHS approval.

Use the issue and PR templates in `.github/` to record reproduction, contract
and output impact, verification, and remaining dependencies. Summarize what
changed and the checks actually run. Distinguish implemented code, built
artifacts, published releases, and downstream adoption; each needs its own
evidence. Do not mark pending release or consumer verification complete.
