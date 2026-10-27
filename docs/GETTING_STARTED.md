# Getting started

This guide covers installation, profile selection, Python API examples, and
command-line use. For the project overview, see the [README](../README.md).
For the complete input/result contract, see
[the integration guide](INTEGRATION_CONTRACT.md).

- [Choose a source and profile](#choose-a-source-and-profile)
- [Installation](#installation)
- [Python API](#python-api)
- [CLI](#cli)

## Choose a source and profile

The recommended profiles in released package **v0.6.0** are:

- `hhs-nofo-fy27-html@0.5.0`: provisional source-native behavior for semantic
  export HTML.
- `hhs-nofo-fy27-pdf-estimate@0.6.0`: recommended PDF-only profile for PDFs
  with a usable structure tree; returns numeric estimates with metric-specific
  reliability and include/exclude sensitivity when tagged content is unknown.
- `hhs-nofo-fy27-generic-pdf-estimate@0.5.0`: fallback for untagged or
  Word-saved PDFs; reconstructs conservative paragraph blocks from visual text
  lines and always labels configured metrics as low-reliability estimates.

These profiles select passive method `0.4.0-provisional`. Historical profiles
remain available unchanged for interpreting earlier results; see the
[profile comparison](PASSIVE_V4_ADOPTION.md#profile-selection). Installing
a new package does not select a new profile or upgrade a deployed consumer.

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

## Installation

Use Python 3.11 or newer. Install the pinned wheel from the
[v0.6.0 release](https://github.com/agilesix/hhs-nofo-metrics/releases/tag/v0.6.0).
The URL fragment makes pip verify the downloaded wheel's SHA-256:

```bash
python -m pip install "https://github.com/agilesix/hhs-nofo-metrics/releases/download/v0.6.0/hhs_nofo_metrics-0.6.0-py3-none-any.whl#sha256=7fc342f8bc0b7f78cf876ef41de847cf09404cdfe1045db10bd908df338ca81c"
```

The release also provides a source distribution. Its published SHA-256 is
`f6b6c3a8c36b9500d6bdf00300be2b530a7226d1db759dd6ff2ccad47181b721`.
Verify the selected artifact against the release metadata before use; do not
substitute a digest from a local candidate build. Lock transitive dependencies
in the consumer's environment too: verifying the wheel does not pin them.

A commit-pinned Git installation is another option for a reviewed source revision:

```bash
pip install "hhs-nofo-metrics @ git+https://github.com/agilesix/hhs-nofo-metrics.git@<commit-sha>"
```

For local development, follow the
[development setup](../CONTRIBUTING.md#development-setup). For learning about
and adopting later releases, see [consumer updates](INTEGRATION_CONTRACT.md#consumer-updates).
This package has no built-in DOCX adapter. NOFO Builder converts Word content
to semantic HTML before calling the same API; that conversion, UI, storage,
targets and upload controls are outside this package.

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

For the HTML example, save the following configuration as `html-adapter.json`
to limit analysis to the element with ID `download_target`:

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

## Development

See [CONTRIBUTING.md](../CONTRIBUTING.md) for environment setup and checks.
[The release process](RELEASE_PROCESS.md) describes versioning, validation,
artifact publication, and consumer adoption. See the
[documentation index](README.md) for methodology and consumer-specific guides.
