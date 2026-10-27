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

## Word export observation

On October 27, 2026, an invented-text DOCX was generated outside this repository
and exported with Microsoft Word for Mac 16.114.1. It has one paragraph inside
one splittable table cell, continued naturally across two pages. Its independent
reference contains 165 document words (including a three-word title), 162
sentence words, 36 sentences in one sentence-bearing paragraph, 18 passive
sentences, 270 syllables, and 936 sentence-token characters. The HTML reference
agrees with those counts. No real or pre-decisional NOFO information was used.

Word's local **Best for printing** export preserves the exact reference text
across two pages but has **no structure tree**. The tagged-PDF profile correctly
rejects it; that route cannot exercise the repair.

The **Best for electronic distribution and accessibility** route, using
Microsoft's online service, returns a tagged two-page PDF. However, it represents
the continuing source cell as **two distinct TH/P objects**, one on each page,
under Table/THead/TR. The same nested P identity is not retained across pages.
Both the published 0.6.0 / adapter 0.1.7 and candidate 0.6.1 / adapter 0.1.8
therefore preserve two sentence-bearing blocks and perform no continuity merge.
They produce identical values under tagged-PDF profile `0.6.0`:

| Builder-displayed measure | Source reference | Released 0.6.0 | Candidate 0.6.1 |
| --- | --- | --- | --- |
| Word Count | 165 | 165 | 165 |
| Words per sentence | 4.5 | 4.5 | 4.5 |
| Sentences per paragraph | 36 | 18 | 18 |
| Flesch-Kincaid Grade Level | 5.83 | 5.83 | 5.83 |
| Passive-sentence percentage | 50 | 50 | 50 |

The page boundary happens between complete sentences in this fixture, so all
162 sentence words and 36 sentences are recovered. That coincidence does not
prove that a sentence split by the same exporter would be recovered correctly.
The paragraph-count mismatch remains, even though four displayed values agree.
Raw PDF text recovery matches the reference, but the normalized adapter also
treats the producer's Title tag as unknown and emits that title after the first
tagged table group. Full normalized reading-order fidelity is not established.

This is a **documented unsupported producer structure**, not a passing Word
continuity validation and not a regression introduced by the candidate. Joining
these distinct objects based on matching text, geometry, or shared table ancestry
would violate the repair's identity guard and could combine genuinely different
cells. The arithmetic was not changed to hide the mismatch. The stable-identity
repair remains covered by the programmatically generated tagged-PDF fixtures;
this Word route does not provide a matching positive producer example.

The source, PDFs, visual QA, and detailed receipts remain outside Git; only this
synthetic aggregate observation is recorded here. Word parity, a positive real
producer example of the repaired structure, the broader real-document release
gate, and authenticated Builder verification remain unestablished. Follow
[the release process](RELEASE_PROCESS.md) before designating an integration
release, using eligible sources and separately approved systems/workflows under
[the public boundary](PUBLIC_REPOSITORY_BOUNDARY.md).

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
