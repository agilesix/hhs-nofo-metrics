# HHS NOFO Metrics

HHS NOFO Metrics is a deterministic Python package for calculating versioned,
reproducible plain-language measurements from an HHS Notice of Funding
Opportunity. It supports source-native semantic HTML, tagged PDFs, and an
explicitly lower-confidence fallback for untagged PDFs.

HHS Office of Grants directs this work and decisions about the measurement
approach. Agile Six implements and maintains the code on its behalf as a
contractor. Hosting does not define program authority or legal/IP ownership;
the existing MIT license and attribution remain unchanged. The bundled profiles
and methods are provisional and do not establish formal HHS approval.

It produces measurements and provenance. It does not make clearance,
compliance, accessibility, legal, policy, or document-quality determinations,
and it does not perform generative-AI review.

## Supported product surface

- One public `analyze()` API accepting PDF inputs or an explicit HTML
  `SourceBundle`, with an explicitly required profile.
- A compact CLI for analysis and contract inspection.
- Six deterministic metrics: Word Count, average words per sentence,
  characters per word, Flesch Reading Ease, Flesch-Kincaid Grade Level, and
  passive-sentence percentage.
- Sentence-scope results also publish the count of sentence-bearing semantic
  blocks and average sentences per paragraph for consumer presentation.
- Versioned profiles and source-free result contracts.
- Reliability-aware PDF estimates for tagged-PDF workflows.
- Three versioned, built-in extraction adapters with a shared internal contract.

Six profiles are bundled. Each source has a corrected passive-classifier
profile introduced in package 0.6.0 and a retained earlier profile:

| Source | Corrected profile | Retained earlier profile |
| --- | --- | --- |
| Semantic HTML | `hhs-nofo-fy27-html@0.5.0` | `hhs-nofo-fy27-html@0.4.0` |
| Tagged PDF | `hhs-nofo-fy27-pdf-estimate@0.6.0` | `hhs-nofo-fy27-pdf-estimate@0.5.0` |
| Generic PDF | `hhs-nofo-fy27-generic-pdf-estimate@0.5.0` | `hhs-nofo-fy27-generic-pdf-estimate@0.4.0` |

The corrected profiles select passive method `0.4.0-provisional`; the retained
profiles use `0.3.0-provisional`. The examples below select corrected profiles.
All profiles remain provisional. Existing integrations should make an explicit
adoption decision and retain earlier result identities; see
[passive-classifier adoption](docs/PASSIVE_V4_ADOPTION.md).

Repository version tags such as `v0.6.0` mark release source commits; GitHub
Releases attach notes and downloadable packages to those tags. See
[tags and the release process](docs/RELEASE_PROCESS.md#what-the-tags-mean) for
naming, component-version differences, automated checks, and publication steps.

For PDF-only workflows that need useful numeric estimates without a separate
manual review artifact, use the PDF-estimate profile. It preserves
source-declared block order, does not fall back to visual-line guessing, and
labels each value `high`, `moderate`, or `low` reliability based on extraction
coverage and the result's sensitivity to including or excluding unknown tagged
content.

If a PDF has no usable structure tree, callers may deliberately select the
generic-PDF estimate profile. It never presents reconstructed flat-PDF
paragraphs as authoritative source structure. Builder integrations should use
semantic HTML whenever it is available.

## Reuse and installation

The existing Python API and CLI support whole-NOFO reuse. Start with
[installation and artifact verification](docs/INSTALLATION.md),
[how and why the measurements work](docs/METHODOLOGY.md), and
[consumer roles and updates](docs/REUSE_AND_UPDATES.md). A new engine or hosted
service is not required. The package accepts PDF or explicit semantic HTML;
Word conversion is currently a Builder adapter outside this package.

As verified on October 27, 2026, the published release is
[0.6.0](https://github.com/agilesix/hhs-nofo-metrics/releases/tag/v0.6.0).
Install its pinned wheel with its recorded SHA-256:

```bash
python3 -m pip install 'hhs-nofo-metrics @ https://github.com/agilesix/hhs-nofo-metrics/releases/download/v0.6.0/hhs_nofo_metrics-0.6.0-py3-none-any.whl#sha256=7fc342f8bc0b7f78cf876ef41de847cf09404cdfe1045db10bd908df338ca81c'
```

Use a virtual environment and lock extraction dependencies for production;
[the installation guide](docs/INSTALLATION.md) includes a separate download,
checksum comparison, and inventory checks. The local 0.6.1 candidate is
unpublished. Release availability, consumer deployment, and policy approval are
separate facts. For local development, use the editable installation below.

## Python API

```python
from hhs_nofo_metrics import NofoMetricsError, analyze

try:
    result = analyze(
        "notice.pdf",
        profile="hhs-nofo-fy27-pdf-estimate@0.6.0",
    )
except NofoMetricsError as error:
    print(error.to_dict())
else:
    payload = result.to_dict()
```

Consumers must inspect each metric's `status` before reading its value. A
calculated or estimated value means the identified method completed; it does
not mean the document passed a review.

`profile` is required. The package has no implicit universal measurement
policy; callers must select the source and reliability contract they intend.

For a tagged PDF estimate:

```python
result = analyze(
    "notice.pdf",
    profile="hhs-nofo-fy27-pdf-estimate@0.6.0",
)

reliability = result.metrics["word_count"].reliability
assert reliability is not None
print(reliability.level, reliability.sensitivity.to_dict())
```

For a system that already owns ordered semantic content, use its export HTML
instead of reverse-engineering reading order from a PDF:

```python
from hhs_nofo_metrics import SourceBundle, analyze

result = analyze(
    SourceBundle.from_html(export_html.encode("utf-8")),
    profile="hhs-nofo-fy27-html@0.5.0",
    adapter_config={"root_id": "download_target"},
    production_path="nofo_builder_export_html",
)
```

## CLI

For the HTML example, save this optional root-selection configuration as
`html-adapter.json`:

```json
{"root_id": "download_target"}
```

```bash
hhs-nofo-metrics analyze notice.pdf \
  --profile hhs-nofo-fy27-pdf-estimate@0.6.0 \
  --output result.json

hhs-nofo-metrics analyze export.html \
  --source-kind html \
  --profile hhs-nofo-fy27-html@0.5.0 \
  --adapter-config html-adapter.json \
  --output result.json

hhs-nofo-metrics analyze tagged-notice.pdf \
  --profile hhs-nofo-fy27-pdf-estimate@0.6.0 \
  --output result.json

hhs-nofo-metrics analyze word-saved-notice.pdf \
  --profile hhs-nofo-fy27-generic-pdf-estimate@0.5.0 \
  --output result.json

hhs-nofo-metrics profiles list
hhs-nofo-metrics adapters list
hhs-nofo-metrics --version
```

Running `hhs-nofo-metrics` without arguments returns a compact content-first
view of the installed profiles, adapters, and useful next commands. Standard
output uses TOON 4.1 by default for concise agent-readable receipts, lists,
details, and errors. Add `--json` anywhere in a command to receive JSON instead:

```bash
hhs-nofo-metrics profiles list --json
```

The analysis result file itself is always written as versioned JSON. Terminal
output is only a receipt and does not replace that stable result artifact.

## Documentation and contributing

[The documentation guide](docs/README.md) maps the contracts, methodology,
integration guides, and adoption records. Development-branch documentation may
include unreleased behavior; the changelog and installed package identities
identify the version being evaluated.

- [Verified release installation](docs/INSTALLATION.md)
- [Reuse, program/maintenance roles, and consumer updates](docs/REUSE_AND_UPDATES.md)
- [Contributing and reporting issues](CONTRIBUTING.md)
- [Repository guidance for agents](AGENTS.md)
- [Security reporting](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [Current architecture](docs/ARCHITECTURE.md)
- [Measurement methodology](docs/METHODOLOGY.md)
- [Consumer-neutral integration contract](docs/INTEGRATION_CONTRACT.md)
- [Release process](docs/RELEASE_PROCESS.md)
- [Passive-classifier adoption](docs/PASSIVE_V4_ADOPTION.md)
- [Nested table continuity candidate and validation](docs/NESTED_TABLE_ADOPTION.md)
- [NOFO Builder consumer guide](docs/consumers/NOFO_BUILDER.md)
- [NOFO Checker integration](docs/NOFO_CHECKER_INTEGRATION.md)
- [Public/private repository boundary](docs/PUBLIC_REPOSITORY_BOUNDARY.md)

## Development

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pre-commit install
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/pytest --cov=hhs_nofo_metrics --cov-report=term-missing
.venv/bin/python tools/check_public_repo.py
.venv/bin/pre-commit run --all-files
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for distribution checks and
[the release process](docs/RELEASE_PROCESS.md) for clean-install and
private-cohort gates.

Private PDFs, Word captures, screenshots, Gartner data, review packets, and
calibration receipts belong outside this repository. Run the public-boundary
check before every release candidate and the history-aware form before any
repository is made public.

## License

This project is available under the [MIT License](LICENSE).
