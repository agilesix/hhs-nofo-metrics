# NOFO Builder consumer guide

This is a non-normative mapping from the consumer-neutral package contract to
NOFO Builder. Builder is one consumer; its persistence, jobs, permissions, and
UI remain outside the package.

## Recommended measurement source

Builder should calculate draft readability metrics from the semantic export
HTML that it already renders, not by reconstructing ordered content from its
PDF. The existing export template orders sections and subsections and emits
semantic headings, paragraphs, lists, and tables inside `#download_target`.

This gives Builder a one-call numeric path without a Builder-specific block
schema or a PDF reconstruction step:

```python
from hhs_nofo_metrics import NofoMetricsError, SourceBundle, analyze

try:
    result = analyze(
        SourceBundle.from_html(render_current_export_html(nofo)),
        profile="hhs-nofo-fy27-html@0.4.0",
        adapter_config={"root_id": "download_target"},
        production_path="nofo_builder_export_html",
        document_id=str(nofo.pk),
        revision=current_builder_revision(nofo),
    )
except NofoMetricsError as error:
    record_failed_attempt(nofo_id=nofo.pk, error=error.to_dict())
else:
    record_success(nofo_id=nofo.pk, result=result.to_dict())
```

`render_current_export_html(nofo)` is intentionally a Builder-owned placeholder.
It should render the same template/context and current database revision used
for the downloadable document and return UTF-8 bytes. It should not make an
authenticated HTTP request back into Builder or manually rebuild a second
content representation.

The HTML result is a `structured_estimate`. Continue to use the designed PDF
for visual, accessibility, metadata, link, and final-output checks. The
tagged-PDF estimate remains available for PDF-only consumers and final-PDF
investigation; it is not the recommended source for Builder's live draft
readability display.

The semantic-HTML and tagged-PDF pipelines converge on the same private
resolved-scope calculation kernel after their source-specific resolution. This
means identical resolved content produces identical numeric metrics without
making PDF reconstruction part of Builder's draft calculation path.

## Current policy behavior

The provisional HTML profile:

- counts selected headings, body text, list items, and table content for the
  standalone Word Count;
- excludes headings, navigation, headers, and footers from sentence-scoped
  readability;
- includes terminally punctuated sentences within body, list, and narrative
  table blocks;
- excludes unpunctuated trailing fragments instead of joining neighboring
  elements; and
- calculates passive-sentence percentage from that same accepted sentence
  inventory using `hhs-nofo-passive-sentence-rule@0.3.0-provisional`.

The profile and warnings must remain visible to consumers. Numeric output is a
versioned measurement, not HHS approval or a pass/fail determination.

## Suggested persistence

Use an append-only analysis table linked to the existing NOFO record. Preserve:

- `analysis_id` and attempt timestamps;
- source SHA-256 and Builder revision;
- result schema and engine version;
- profile ID, version, status, and SHA-256;
- the complete successful result JSON;
- stable error code/message for failed attempts; and
- status plus nullable value for any flattened metric fields.

Display the latest successful result whose Builder revision, HTML SHA-256, and
profile reference still match the current source. Never coerce
`not_configured` or `unable_to_calculate` to zero.

## Validation status

The semantic HTML path has been exercised against a frozen ten-document Builder
cohort and a matched HTML/PDF diagnostic cohort. It avoids the sentence
inflation introduced when Word opens a designed PDF, and warm analysis of
realistic Builder exports completes in well under one second on the development
baseline.

This supports a contained feature-flagged integration, not promotion of the
provisional HHS method. Before broad release, verify that the export HTML and
downloadable document use the same source revision and repeat the frozen-cohort
acceptance check in the target runtime.
