# Integration contract

This is the consumer-neutral boundary for `hhs-nofo-metrics`. NOFO Builder, NOFO
Checker, batch jobs, and future consumers use the same API. Persistence,
orchestration, UI, thresholds, and clearance decisions remain consumer-owned.
Start with the [public package and installation guide](../README.md), then
read the [methodology](METHODOLOGY.md) for content selection and calculation
limits. The API and CLI do not require Django or another application framework.
Direct Python reuse or CLI invocation can share execution without a new service.
A consumer-hosted wrapper is a later integration option, not part of this contract.

## Python API

```python
from hhs_nofo_metrics import NofoMetricsError, analyze

try:
    result = analyze(
        pdf_source,
        profile="hhs-nofo-fy27-pdf-estimate@0.6.0",
        production_path="consumer_supplied_label",
        document_id="optional-consumer-id",
        revision="optional-consumer-revision",
    )
except NofoMetricsError as error:
    error_payload = error.to_dict()
else:
    result_payload = result.to_dict()
```

PDF input may be a path, bytes-like object, or binary stream. Seekable streams
are read from the beginning and restored to their original position. The
package does not close caller-owned streams.

`profile` is required. The package has no universal default because HTML,
reliability-rated tagged PDF, and generic flat-PDF fallback make materially
different scope and reliability decisions.

For semantic export HTML:

```python
from hhs_nofo_metrics import SourceBundle, analyze

result = analyze(
    SourceBundle.from_html(html_bytes),
    profile="hhs-nofo-fy27-html@0.5.0",
    adapter_config={"root_id": "download_target"},
    production_path="structured_export_html",
)
```

HTML must be UTF-8. `root_id` is optional; when present, analysis is limited to
that element and fails if it is absent.

## Profiles and source behavior

- `hhs-nofo-fy27-html@0.5.0` uses DOM order and semantic element boundaries.
  It is the recommended NOFO Builder draft-metrics path.
- `hhs-nofo-fy27-pdf-estimate@0.6.0` requires a usable PDF structure tree,
  includes unknown tagged blocks, and reports per-metric reliability based on
  coverage and include/exclude sensitivity.
- `hhs-nofo-fy27-generic-pdf-estimate@0.5.0` accepts PDFs without usable tags,
  reconstructs conservative paragraph blocks from visual text lines, and
  applies a low reliability ceiling to every configured metric. It is a
  fallback for cases such as Word-saved PDFs, not the preferred NOFO Builder path.

These v0.6.0 recommendations use corrected passive method
`0.4.0-provisional`. Earlier profiles remain deliberately available for
historical calculations; the [adoption guide](PASSIVE_V4_ADOPTION.md) lists both.
The package accepts PDF and HTML sources, not DOCX. NOFO Builder owns the Word
conversion adapter and import transformations. A different consumer must make
its own explicit source contract rather than assume those transformations ship
inside the metrics package.

When `adapter` is omitted, the profile's pipeline chooses its versioned
default. An incompatible explicit adapter fails rather than silently changing
pipelines. Built-in results do not expose extracted source text or temporary
materialization paths.

## Result contract

Successful analysis returns `AnalysisResult`. Results without reliability use
`analysis-result-1.1.0.json`; reliability-aware PDF estimates use the additive
`analysis-result-1.2.0.json` schema.

Important top-level fields are:

| Field | Meaning |
| --- | --- |
| `schema_version` | Shape and validation rules for the result |
| `engine` | Package implementation identity |
| `source` | Source hash, caller identifiers, and bounded metadata |
| `adapter` | Extraction identity, coverage, configuration, and dependencies |
| `profile` | Versioned scope and method policy |
| `result_basis` | Rendered-PDF measurement or structured-source estimate |
| `methods` | Versioned calculation components |
| `coverage` | Extraction and classification completeness |
| `selection` | Per-metric inclusion/exclusion summary |
| `metrics` | Status-aware values, components, reasons, and reliability |
| `warnings` | Non-fatal limitations consumers must retain |

All product paths resolve two scopes: document content for Word Count and
complete sentences for sentence-scoped metrics. They use the same token,
count, syllable, and readability kernel. The generic-PDF path first performs a
versioned, conservative line-to-paragraph reconstruction and reports the
resulting uncertainty instead of treating visual lines as source paragraphs.

The selected profile's explicit `include_roles`, `exclude_roles`, and
`unknown_role_policy` values are the scope-policy data. The engine groups those
rules into the two scopes and does not replace them with hard-coded HHS role
lists. Consumers can inspect the profile and method identities to derive a
human-readable explanation of the active behavior.

## Metric status

Consumers must read `metrics.<id>.status` before its value:

- `calculated`: a configured deterministic method completed.
- `estimated`: a numeric value and `reliability` are present.
- `unable_to_calculate`: no value; `reason` explains why.
- `not_configured`: no calculation method is attached by the selected profile.

The current profiles configure Word Count, average words per sentence,
characters per word, Flesch Reading Ease, Flesch-Kincaid Grade Level, and
passive-sentence percentage. A numeric value does not mean a document passed
policy, accessibility, clearance, legal, or quality review. There is no overall
pass or readiness status.

Reliability is metric-specific and includes a versioned method, level
(`high`/`moderate`/`low`), extraction and classification coverage, unknown
content counts, and include/exclude sensitivity. The current bands are
calibration hypotheses, not HHS policy.

## Errors and CLI

Expected Python failures raise `NofoMetricsError` subclasses with `to_dict()`.
Stable categories are `adapter_not_found`, `adapter_contract_error`,
`adapter_execution_error`, `dependency_error`, `input_error`, `profile_error`,
`analysis_error`, and `nofo_metrics_error`.

The CLI returns `0` for success, `2` for usage errors, and `1` for expected
runtime failures. Standard output contains a compact TOON 4.1 receipt or error
by default; add `--json` to receive JSON. Standard error is reserved for
unexpected diagnostics.

```bash
hhs-nofo-metrics analyze input.pdf \
  --profile hhs-nofo-fy27-pdf-estimate@0.6.0 \
  --output result.json
```

## Versioning and consumer responsibilities

Consumers should retain the complete result and compare the package, schema,
profile, method, adapter, configuration, and dependency identities they
support. Unknown schema versions must be rejected. Repeated analysis with the
same source and identities reproduces metrics, coverage, selection, and
warnings; invocation ID and timestamp differ.

The package does not persist results, schedule work, retrieve external files,
render UI, manage permissions, or translate metrics into pass/fail. Private
calibration tools and evidence are not part of the package or its compatibility
contract.

## Consumer updates

1. Follow [GitHub releases](https://github.com/agilesix/hhs-nofo-metrics/releases).
   GitHub users can select **Watch → Custom → Releases** on the repository;
   consumers may also use an agreed working contact for release notices.
   Review the [changelog](../CHANGELOG.md) and profile/method changes, not only
   the package version. Publishing code does not deploy it into another system.
2. Pin the chosen release artifact and verify its published digest as described
   in [installation](../README.md#installation). Pin the exact profile and
   supported schema, adapter/configuration and dependency identities. Record
   the consumer's content-selection/conversion revision as well.
3. Test the intended source path before explicitly upgrading the consumer.
   Shared formulas cannot guarantee equal values when systems extract or select
   different content. Whole-NOFO aggregation is the supported scope here;
   section/subsection/paragraph authoring assistance is not provided by this offer.
4. Retain saved results with their original measurement identities and any
   consumer targets. Recalculation under a new contract is a new observation,
   not a silent rewrite of history. Do not compare changed contracts as if only
   the NOFO text had changed.

HHS Office of Grants directs the work and measurement approach. Agile Six
implements and maintains code on its behalf as a contractor. Repository hosting
does not define legal/IP ownership, licensing or formal method approval. The
existing [MIT license](../LICENSE) and provisional method status are unchanged.
