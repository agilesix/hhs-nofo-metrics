# Repository guidance for agents

## Start here

Read [README.md](README.md), [CONTRIBUTING.md](CONTRIBUTING.md), and the relevant
contract before editing behavior. [docs/README.md](docs/README.md) maps the
available documentation. Check the working tree and preserve existing work.

This package calculates deterministic NOFO metrics and provenance. Consumers
own orchestration, persistence, permissions, UI, thresholds, and clearance
interpretation. Keep those responsibilities outside the package.

## Public repository: no pre-decisional NOFO information

This repository is public. Do not use pre-decisional NOFOs or pre-decisional
information about NOFOs as inputs, fixtures, examples, evidence, or context for
work in this repository. Do not copy, extract, save, stage, commit, or publish
that material here, including excerpts, metadata, reviewer comments, screenshots,
logs, generated reports, and other derivatives that disclose it. This applies
to local, temporary, untracked, and ignored files as well as Git history and
public issues, PRs, comments, and attachments. A `.gitignore` entry is not a
sensitivity safeguard or permission to store the material here.

Each user/contributor is responsible for confirming that information they supply
or authorize for this work is not pre-decisional and is eligible for public
release under applicable HHS Rules of Behavior,
data-sensitivity and information-handling requirements, and cybersecurity
policies. An agent, repository check, or successful test cannot make that
clearance decision or establish policy compliance on the user's behalf.

Use synthetic examples by default. If a source's status is unclear, do not
access, process, or save it for repository work; use a synthetic substitute
until the responsible user confirms its public-release eligibility. Even
publicly released source corpora remain outside Git under
[the public boundary](docs/PUBLIC_REPOSITORY_BOUNDARY.md). Private evaluation
requires separately approved systems and workflows; moving a file outside Git
does not by itself authorize its use.

## AI assistance

Follow [AI use and contribution guidance](docs/AI_USE.md). It does not supersede
applicable HHS or organizational policies or authorize a tool/data flow.
Keep the built-in metric paths deterministic and versioned; introducing runtime
AI needs a separate explicit proposal, evaluation, and applicable approvals.
Do not fabricate evidence or treat generated tests/reviews as independent human
validation. State material AI assistance and checks actually performed in PRs;
keep sensitive prompts and transcripts out of the public repository. Human
accountability and release/deployment authorization requirements remain in force.

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

- Re-check the [methodology summary](docs/METHODOLOGY.md#in-brief) and
  [README summary](README.md#how-the-metrics-are-calculated) whenever content
  selection, sentence rules, formulas, input handling, or reliability changes.
  This includes changes in `methods/`, `adapters/`, `profiles/`,
  `metric_scopes.py`, `resolved_scope.py`, or `semantic_html_engine.py` under
  `src/hhs_nofo_metrics/`. Update both summaries in the same PR as needed;
  re-check the HHS/Builder section when guidance or consumer behavior changes.
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

## Release decisions and versioning

Follow [repository access and approvals](docs/REPOSITORY_ACCESS.md). Merge
permission follows repository Write, Maintain, or Admin access. Another person's
PR approval is optional; eligible users may merge their own PRs after required
CI passes and review discussions are resolved. Ben and Mike remain the designated
release operators. Do not bypass CI, change access controls
to unblock a merge, or treat agent review as independent human approval. The release
environment must be used by future publishing jobs; it does not gate manual
GitHub Releases or downstream deployments.

Read [the release policy](docs/RELEASE_PROCESS.md) before preparing a release.
A merge is not a publication or consumer deployment. Do not wait for unrelated
open PRs; identify actual dependencies and freeze the intended release scope.
Record the scope/timing agreement and technical review in a release PR or issue.
The initial working convention is Ben/Mike or designated maintainers; technical
release agreement does not establish formal HHS method approval.

Use patch versions for compatible bug fixes, minor versions for compatible new
capabilities, and major versions after 1.0 for incompatible public contracts.
During 0.x, use a new minor version for intentional incompatibilities. A patch
can change corrected scores: advance changed measurement-component identities,
preserve released contracts, and explain output impact. Do not publish or deploy
solely because implementation/merge was requested; use explicit authorization
for those actions. A local candidate version or green CI does not replace the
release decision and required evidence gates. Document mismatches and limits
rather than claiming all producer formats are repaired.

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
