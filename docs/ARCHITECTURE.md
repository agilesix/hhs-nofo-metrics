# Architecture

## Purpose and boundary

`hhs-nofo-metrics` owns deterministic document measurement, versioned method and
profile identities, source-bound provenance, status-aware metric results, and
the internal extraction-adapter contract. Consumers own orchestration, persistence,
permissions, user interfaces, dashboards, pass/fail interpretation, and
clearance decisions.

The exact rendered PDF remains the authoritative final-output source. A
structured source may provide a more reliable readability estimate before
rendering because its reading order and block semantics are explicit.

## Public surface

The supported Python surface is exported by `hhs_nofo_metrics`:

- `analyze()` with an explicitly required profile;
- profile and adapter inspection;
- PDF/source-bundle input types;
- result models; and
- stable expected-error categories.

The supported CLI exposes only `analyze`, `profiles`, `adapters`, and version
inspection.

## Runtime flow

```text
PDF or semantic HTML source
  -> materialized source bundle
  -> profile-selected analysis pipeline
  -> extraction and exact coverage ledger
  -> source-specific resolution and versioned selection
  -> private resolved document/readability scopes
  -> shared token, count, and readability kernel
  -> source-free, status-aware result
```

Profiles own pipeline selection. There are three intentional runtime paths:

1. `hhs-semantic-html-analysis@0.1.0` consumes ordered semantic HTML blocks,
   applies the provisional HHS document and sentence scopes mechanically, and
   returns a source-free `structured_estimate` without PDF reconstruction.
2. `hhs-tagged-pdf-estimate-analysis@0.1.0` uses the tagged-PDF adapter and
   metric kernel, includes unknown tagged blocks in the primary estimate, and
   reports metric-specific reliability from extraction coverage and
   include/exclude sensitivity. It remains unable when no usable structure tree
   exists.
3. `hhs-generic-pdf-estimate-analysis@0.1.0` accepts PDFs without usable tags,
   conservatively reconstructs paragraph blocks from visual text lines, uses
   the shared metric kernel, and caps every configured metric at low
   reliability.

All three paths converge on the same private `ResolvedMeasurementScope` and
shared metric kernel after source-specific resolution. HTML supplies
authoritative ordered blocks directly. Tagged PDF supplies source-declared
structure groups and calculates both include-unknown and exclude-unknown
scenarios. Generic PDF reconstructs flat lines conservatively and publishes
that limitation. Identical resolved content therefore produces identical
numeric metrics.

The shared kernel does not require the source representations to produce equal
scopes. A PDF may remain provisional or unable, and a genuine rendered-output
difference may produce a diagnostic delta. Alignment means one policy and
calculation boundary after resolution, not forced numerical parity.

## Internal module responsibilities

| Area | Responsibility |
| --- | --- |
| `api.py` | Public orchestration and pipeline dispatch |
| `analysis_pipelines.py` | Immutable profile-to-pipeline registry |
| `sources.py` | Caller input normalization and isolated materialization |
| `adapters/` | Supported generic PDF, tagged-PDF, and HTML adapters plus their internal contract |
| `adapters/tagged_structure.py` | Minimal tagged-PDF structure and geometry extraction primitives |
| `pdf_reflow.py` | Conservative flat-PDF line-to-paragraph reconstruction and diagnostics |
| `metric_scopes.py` | Generic grouping of profile-declared metric rules into document and readability scopes |
| `resolved_scope.py` | Private source-neutral document/readability scope and shared calculation kernel |
| `methods/` | Shared tokens, passive classification, deterministic arithmetic, and frozen v1 primitives |
| `models/` | Public domain, profile, and result contracts |
| `profiles/` and `schemas/` | Packaged immutable product contracts |

Metric inclusion and exclusion policy is profile data, not an engine constant.
`metric_scopes.py` only enforces the generic architecture: standalone Word
Count has one document-content rule, and every sentence-scoped metric shares
one readability rule. A profile may intentionally declare different roles or
unknown-content handling. Human-readable policy tables can therefore be
derived from the selected profile plus its versioned method identities.

Only source-free result schemas cross the package boundary. Private
text-bearing calibration evidence and experimental adjudication machinery are
kept outside the release repository and package distribution.

## Adapter policy

The product distribution registers exactly three supported built-in adapters:
`hhs-pdf-adapter`, `hhs-tagged-pdf-adapter`, and
`hhs-semantic-html-adapter`. The release does not discover or execute
third-party adapters. A future extension mechanism requires a separately
reviewed product contract and must preserve the source-free result boundary.

Producer-specific experiments do not ship as built-ins. A production adapter
must earn support through reviewed fixtures and the common conformance contract
before it enters the default registry.

## Invariants

- No source text or local materialization path appears in built-in result JSON.
- Every output-affecting method, adapter, profile, pipeline, and schema is
  versioned.
- Unsupported structured sources fail closed; incomplete tagged scope either
  fails closed or produces an explicitly reliability-rated estimate according
  to the selected profile.
- Word Count and readability-sentence selection remain separate.
- Eligible semantic HTML and tagged-PDF scopes use the same shared token
  and readability kernel.
- Passive voice uses an explicitly provisional, independently versioned method;
  consumers must not present it as HHS-approved or Microsoft Word-equivalent.
- No runtime result contains an overall pass, readiness, or clearance status.
- Product behavior changes require explicit profile or method versioning.
