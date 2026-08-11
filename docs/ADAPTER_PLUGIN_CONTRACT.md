# Adapter plugin contract

This document describes the implemented `1.0.0` extraction-adapter contract.
It lets source-specific extractors produce the same normalized input for the
metric engine without moving metric policy into those extractors.

The product distribution registers three built-in implementations:
`hhs-pdf-adapter`, `hhs-semantic-html-adapter`, and
`hhs-tagged-pdf-adapter`. The `pdf`, `html`, and `tagged-pdf` aliases resolve to
them. Producer-specific experiments are not discoverable from the installed
product.

## Responsibilities

The core package owns source materialization and hashing, adapter selection and
validation, profiles, metric policy and methods, built-in text-free
serialization, and typed expected errors. Third-party plugins are trusted code:
the contract rejects materialized paths but cannot determine whether an
arbitrary evidence value or warning repeats source content.

An adapter owns support evidence, text and structural extraction, locations,
reading order, roles, confidence, warnings, and honest extraction coverage. It
must return deterministic output for frozen inputs and configuration.

An adapter cannot set `Segment.inclusion_override`, silently fall back to
another adapter, or claim a different primary source hash.

## Source bundles

Callers may pass a PDF path, bytes, or binary stream and must select a profile:

```python
from hhs_nofo_metrics import analyze

result = analyze(
    "notice.pdf",
    profile="hhs-nofo-fy27-generic-pdf-estimate@0.4.0",
    adapter="pdf",
)
```

Adapters that accept auxiliary artifacts use a `SourceBundle`:

```python
from hhs_nofo_metrics import SourceArtifact, SourceBundle, analyze

source = SourceBundle(
    primary=SourceArtifact(
        name="primary",
        kind="pdf",
        source="notice.pdf",
        media_type="application/pdf",
    ),
    auxiliaries=(
        SourceArtifact(
            name="builder_manifest",
            kind="json",
            source="render-manifest.json",
            media_type="application/json",
        ),
    ),
)
result = analyze(
    source,
    profile="hhs-nofo-fy27-generic-pdf-estimate@0.4.0",
    adapter="builder-render-manifest@0.1.0",
)
```

The core hashes and materializes every artifact. Local paths never enter the
public result. A future render-manifest adapter must also validate that the
manifest's declared PDF hash matches the primary artifact before using a
manifest block.

## Plugin implementation

Plugins implement `AdapterPlugin` and expose their descriptor without requiring
construction. This lets discovery list plugins without running plugin setup.

```python
from hhs_nofo_metrics.adapters import (
    AdapterCoverage,
    AdapterDescriptor,
    AdapterResult,
    SupportAssessment,
)


class ExampleAdapter:
    descriptor = AdapterDescriptor(
        id="example-adapter",
        version="1.0.0",
        source_kinds=("pdf",),
        capabilities=frozenset(
            {"text", "page_geometry", "logical_roles", "reading_order"}
        ),
        distribution="example-package",
        distribution_version="1.0.0",
    )

    def inspect_support(self, source):
        return SupportAssessment(status="supported")

    def extract(self, source, *, config):
        document = build_normalized_document(source.primary.path)
        return AdapterResult(
            document=document,
            artifacts_consumed=("primary",),
            capabilities_used=self.descriptor.capabilities,
            coverage=AdapterCoverage(status="complete"),
        )
```

The normalized document's adapter identity, source kind, and source SHA-256
must match the descriptor and primary artifact. Existing normalized-document
rules still require unique segment IDs and monotonic reading order.

## Registration and selection

External distributions register a class or object through a Python entry
point:

```toml
[project.entry-points."hhs_nofo_metrics.adapters"]
example = "example_package.adapter:ExampleAdapter"
```

The exported class or object must expose an `AdapterDescriptor` as
`descriptor`. A class is constructed only when support inspection or extraction
is requested. Duplicate `id@version` references and incompatible contracts are
rejected.

Callers select source-aware behavior explicitly:

```python
result = analyze(
    "notice.pdf",
    profile="hhs-nofo-fy27-generic-pdf-estimate@0.4.0",
    adapter="example-adapter@1.0.0",
)
```

A bare adapter ID works only when exactly one installed version exists. PDF
producer metadata may support an inspection assessment, but does not
authenticate the production tool or authorize automatic selection.

Producer metadata may support an inspection assessment, but does not
authenticate a production tool or authorize automatic selection. A future
producer-specific plugin must earn support through frozen fixtures and the
common conformance contract before a consumer allowlists it.

## Configuration and provenance

`adapter_config` must contain JSON values. The canonical JSON SHA-256 is stored
in the result; the values are not. Do not put credentials in adapter
configuration.

Results record source artifact hashes and sizes; adapter contract,
distribution, dependencies, capabilities, and coverage; configuration hash;
support evidence; and the empty fallback history. Built-in adapter results
contain no extracted source text or local paths. Consumers that require that
guarantee for third-party adapters must allowlist reviewed plugins.

## CLI

```text
hhs-nofo-metrics adapters list
hhs-nofo-metrics adapters show hhs-pdf-adapter@0.4.0
hhs-nofo-metrics adapters inspect notice.pdf --adapter pdf
hhs-nofo-metrics analyze notice.pdf --adapter example-adapter@1.0.0 \
  --adapter-config config.json --output result.json
hhs-nofo-metrics analyze notice.pdf --adapter builder-render-manifest@0.1.0 \
  --aux builder_manifest=render-manifest.json --output result.json
```

`adapters inspect` is advisory and emits `selection_performed: false`. It does
not run metrics or choose an adapter.

## Conformance

External plugin tests should run the reusable conformance function over frozen,
small, redistributable fixtures:

```python
from hhs_nofo_metrics.adapters import run_adapter_conformance
from hhs_nofo_metrics.sources import materialize_source_bundle

with materialize_source_bundle(source_bundle) as source:
    report = run_adapter_conformance(ExampleAdapter(), source)

assert report.to_dict()["conformant"] is True
```

The runner validates source compatibility, support assessment, output shape,
hash and adapter identity, absence of policy overrides, and deterministic
output. Source-specific golden fixtures remain the plugin's responsibility.

## Errors, fallback, and migration

Expected adapter failures retain machine-readable codes:

- `adapter_not_found`
- `adapter_contract_error`
- `adapter_execution_error`

There is no fallback chain in contract `1.0.0`. A consumer retrying with the
generic PDF adapter must make a separate explicit call and retain both attempts
in its orchestration record.

Existing generic PDF callers require no input migration. The `pdf` alias,
path/bytes/stream inputs, profiles, and metric values remain available. New
analyses emit analysis-result `1.1.0`, which adds artifact and adapter
provenance. The historical `1.0.0` schema remains unchanged. Consumers must add
`1.1.0` to their supported schema versions before accepting new results.
