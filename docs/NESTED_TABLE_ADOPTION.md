# Nested table paragraph continuity

Issue: [metrics #12](https://github.com/agilesix/hhs-nofo-metrics/issues/12).
Candidate package: **0.6.1**. Tagged adapter: **0.1.8**.
Resolver: `pdf-tagged-structure-group-resolver@0.3.8`.
Release publication and downstream verification are pending.

## Reproduction and reference

The synthetic fixture generator committed in
`tests/test_nested_table_continuity.py` writes actual two-page PDF content
streams and an indirect Document / Table / TR / TD (or TH) / P structure tree.
It exercises both MCR dictionaries with page references and inline Span
children with inherited page references and integer MCIDs. It does not assert
PDF accessibility conformance or model every producer's export structure.

On package 0.6.0 / adapter 0.1.7, a single P containing “Applications must be”
on page 1 and “reviewed by staff. Submit complete forms.” on page 2 extracts as
separate page-local blocks. The first three words are excluded from sentence
scope, which then reports 6 words and 0% passive sentences. This was reproduced
against the latest main before implementation, rather than inferred from the
historical Builder observation.

The independent reference is the literal source text, with these counts:

| Measure | Reference |
| --- | --- |
| Document words | 9 |
| Sentence words | 6 + 3 = 9 |
| Sentences | 2 |
| Sentence-bearing paragraphs | 1 |
| Words per sentence | 9 / 2 = 4.5 |
| Sentences per paragraph | 2 / 1 = 2 |
| Syllables | 4 + 1 + 1 + 2 + 1 + 1 + 2 + 2 + 1 = 15 |
| Flesch-Kincaid grade | 0.39 × (9 / 2) + 11.8 × (15 / 9) − 15.59 = 5.83 rounded |
| Passive sentences | 1 / 2 = 50% |

Tests assert recovered text, ordering, block count, page provenance, metric
values, and denominators directly against this reference under both tagged
PDF profiles (0.5.0 and 0.6.0). They do not derive the expected counts from
another call to the same PDF extractor. Separate paragraphs in one cell,
headings, adjacent cells, inline spans, mixed direct/nested cell content, and
the existing direct-cell behavior have regression coverage.

## Supported structure and limits

The resolver now gives semantic blocks grouped under TD/TH their own
traversal-local identity, while also retaining the enclosing cell identity. Inline spans inherit
the nearest semantic block. Only the same declared paragraph can join across
pages, subject to the existing consistent-role, consistent-basis, distinct-page,
and no-warning guards. The merged block retains its first page and separate
page bounding boxes in the internal provenance map.

Different paragraphs and headings stay separate, including on the same page.
Headings do not participate in paragraph continuity. Newly exposed paragraphs and headings retain the
existing table metric role; this change does not introduce a heading-scope
policy change. Direct TD content and inline-only spans still support continuity.
Direct cell content mixed with semantic descendants stays page-local to avoid
bridging those descendants. Direct TH content is not newly made eligible for
continuity; a declared P inside TH is eligible.

Other semantic containers inside cells (such as LBody, Note, Caption, and
TOCI) retain their existing grouping and metric roles; their nested paragraph
boundaries are outside this repair.

No continuity is inferred between separate P objects, even if a producer
intended them as one paragraph. Malformed/conflicting MCIDs, unsupported custom
role mappings, untagged content, and text in unsupported objects retain the
existing limitations. The repair uses source structure, never punctuation,
visual proximity, or matching cell text. Formulas, released profiles, passive
methods, and result schemas are unchanged.

No authorized Word-generated equivalent was supplied with this issue or found
in the repository. Actual Word-export structure has **not** been verified;
synthetic results are not Word parity evidence. Private examples and receipts
must stay outside Git. Follow the private real-document gate in
[the release process](RELEASE_PROCESS.md) before designating an integration
release.

## Release and Builder dependency

1. Release package 0.6.1 with adapter 0.1.8 / resolver 0.3.8 after the package
   and private real-document gates pass. Keep 0.6.0 available to reproduce the
   previous extraction. The source change alone does not publish a release.
2. Builder must adopt the released package or its immutable release commit;
   explicit adapter consumers must update their adapter reference to 0.1.8.
   Profile 0.5.0 may remain selected; opting into profile 0.6.0 is the separate
   passive-method decision documented in [passive adoption](PASSIVE_V4_ADOPTION.md).
3. Verify an authenticated upload/report through Builder's existing shared
   pipeline using an authorized PDF with a continuing nested paragraph. Check
   recovered text and sentence/paragraph denominators against the source, then
   all five displayed measures and extraction provenance. Record package,
   adapter, profile, and the verification receipt outside this public repository.
4. Track that adoption and verification under
   [Builder #1059](https://github.com/HHS/simpler-grants-pdf-builder/issues/1059).
   Metrics #12 is not fully accepted until release and downstream verification
   dependencies are satisfied. This work changes no deployment or pilot flags.
