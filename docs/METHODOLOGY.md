# Whole-NOFO measurement methodology

Status: **provisional implementation; not HHS-approved**. This guide describes
aggregate measurements for one supplied NOFO source under an explicit profile.
It does not define section-by-section, paragraph-level, or inline writing
analysis, or reproduce Announcement Module's additional functionality.

HHS Office of Grants directs the work and decisions about the measurement
approach. Agile Six implements and maintains the code on its behalf as a
contractor. That program role does not establish legal/IP ownership or formal
approval of every provisional method. See [roles and reuse](REUSE_AND_UPDATES.md).

## Evidence and authority

The implementation reference here is the published
[0.6.0 release](https://github.com/agilesix/hhs-nofo-metrics/releases/tag/v0.6.0),
commit `b38496f5b90e88b0491d658a3151b04b299add53`. Its corrected profiles are
HTML `0.5.0`, tagged PDF `0.6.0`, and generic PDF `0.5.0`; see the complete
[profile comparison](INTEGRATION_CONTRACT.md#profiles-and-source-behavior).
All three earlier profiles remain supported. The corrected profiles change the
passive classifier, not the other formulas or selection rules.

Three different kinds of statements appear below:

- **Implemented behavior** is checked against packaged profiles, code, and
  synthetic examples. This establishes what the package does.
- **Design rationale** explains the purpose of a current selection or heuristic.
  It is a provisional engineering interpretation, not a newly established HHS
  requirement or evidence that the heuristic recognizes every case.
- **Unresolved policy/evidence** identifies where approved guidance, producer
  evidence, or further validation is still needed. No approved source for every
  inclusion/exclusion rationale is established by the materials cited here.

The accepted [reuse recommendation and roles clarification](https://github.com/HHS/simpler-grants-pdf-builder/issues/1234)
provide program context. Package profiles and method identities are the
machine-readable implementation authority, not substitutes for policy approval.
The unpublished 0.6.1 nested-table repair is described separately in
[nested table adoption](NESTED_TABLE_ADOPTION.md); it is not part of 0.6.0.

## Two scopes and their purpose

The package first resolves ordered blocks, assigns roles, and applies the
selected profile's rules. Only then does it count words or construct the
sentence inventory. A metric therefore depends on extraction and selection as
well as arithmetic.

1. **Document content** supplies standalone Word Count. It includes recognized
   headings, body, lists, and table content, including selected fragments.
2. **Readability sentences** supply words per sentence, characters per word,
   both Flesch metrics, and passive-sentence percentage. They use only accepted
   sentence text in selected body, list, and table blocks.

The rationale is denominator consistency: words in a heading or trailing
fragment must not increase words-per-sentence without a corresponding accepted
sentence. Document Word Count instead describes the selected content volume.
It is not the readability-word numerator and need not equal a word processor's
whole-file count.

A "sentence" here is an operational punctuation-based unit, not a grammatical
judgment. `Apply now.` is accepted in a body block; `Required documents` is a
fragment. Punctuation and a fixed abbreviation/decimal/URL protection rule
bound splitting; the method does not prove that every accepted unit is a
complete grammatical sentence. It never combines different semantic blocks
merely to create a sentence. See
[the sentence method](../src/hhs_nofo_metrics/methods/semantic_blocks.py).

## Counts, formulas, and unavailable values

Let **D** be document words, **R** accepted-sentence words, **S** accepted
sentences, **C** characters in those words, **Y** their estimated syllables,
**A** sentences classified passive, and **P** selected blocks containing at
least one accepted sentence.

| Measure | Calculation | Interpretation |
| --- | --- | --- |
| Word Count | D | Selected document-content volume |
| Words per sentence | R / S | Average length of accepted sentence units |
| Characters per word | C / R | Length of readability token surfaces |
| Flesch Reading Ease | 206.835 − 1.015 × (R / S) − 84.6 × (Y / R) | Formula score using sentence length and syllable density |
| Flesch-Kincaid Grade Level | 0.39 × (R / S) + 11.8 × (Y / R) − 15.59 | Grade-level formula estimate, not a reader assessment |
| Passive-sentence percentage | 100 × A / S | Percentage of accepted sentences matching the provisional classifier |
| Sentences per paragraph | S / P | Published component for consumer display, not a seventh top-level metric |

P counts sentence-bearing **semantic blocks**. A list item or table cell may
be one such block; it is not a count of every visual paragraph or blank line.
Blocks consisting only of fragments do not increase P. Extraction changes can
therefore change sentences per paragraph without a formula change.

The implementation uses unrounded counts in arithmetic. It serializes the five
noninteger top-level metric values with Python `round(value, 2)` and includes
`components.unrounded_value`. Word Count remains an integer;
`components.sentences_per_paragraph` retains the computed ratio. Consumers own
additional display formatting, targets, and bands. They must not recompute a
Flesch score from already rounded words-per-sentence. Scores are not clamped to
a preferred range. See [arithmetic](../src/hhs_nofo_metrics/methods/hhs_draft.py)
and [result construction](../src/hhs_nofo_metrics/semantic_html_engine.py).

An empty document scope can produce Word Count 0. With no accepted sentences,
the sentence-based values are `unable_to_calculate`, with null values and a
reason, rather than zero scores. Results can also be `calculated`, `estimated`,
or `not_configured` according to the contract. All bundled profiles configure
the six metrics. Consumers must check status before reading value and retain
warnings and PDF reliability; see [the result contract](INTEGRATION_CONTRACT.md).

## Worked example

```html
<h2>Eligibility</h2>
<p>Applications must be reviewed by staff. Submit complete forms.</p>
<p>Required supporting documents</p>
```

Under HTML profile `hhs-nofo-fy27-html@0.5.0`:

- D = 13: one heading word, nine words in accepted sentences, and three fragment
  words. The heading and fragment affect document Word Count only.
- R = 9, S = 2, P = 1. The sentences have six and three words.
- C = 52; Y = 15 (4 + 1 + 1 + 2 + 1 + 1 + 2 + 2 + 1).
- A = 1: the first sentence is classified passive; the second is active.
- Words per sentence = 4.5; sentences per paragraph = 2; characters per word =
  5.78; Flesch Reading Ease = 61.27; grade level = 5.83; passive percentage = 50.

This is a synthetic reference with enumerated counts, not a Word calibration or
an approved target. Moving the same words into navigation or separate blocks
can change these totals because the measurement source changed.

## Token, character, and syllable methods

The six profiles share these implementation identities:

| Component | Method reference |
| --- | --- |
| Shared word stream | `hhs-nofo-readability-token-stream@0.1.0-internal` |
| Token/character rules | `word-readability-character-token-candidate@0.1.0` |
| Syllable estimate | `word-syllable-candidate@0.1.0` |
| Semantic sentence split | `hhs-semantic-block-sentence-segmentation@0.1.0` |
| Arithmetic | `hhs-nofo-readability-arithmetic@0.1.0-draft` |

Words start from nonwhitespace chunks. Listed bullet/check markers are ignored;
slashes, backslashes, `://`, and en/em dashes split units. Internal hyphens and
apostrophes can remain in a token. Quotes and selected punctuation are removed
with context-sensitive terminal-punctuation rules and bounded abbreviation
exceptions. This is not simply counting alphabetic words or stripping every
punctuation mark. C sums the lengths of the resulting token surfaces, excluding
interword spaces but potentially retaining internal punctuation and numerals.

Syllables are estimates, not pronunciations from a complete dictionary.
Ordinary words use Unicode normalization and an ASCII vowel-group heuristic
with suffix adjustments and a small exception table. Numeric patterns use a
digit/decimal/currency rule; mixed letter-digit identifiers receive one syllable.
Electronic strings use component heuristics. These bounded choices aim for a
reproducible approximation; they do not establish language-wide accuracy or
Word parity. Approved treatment of names, acronyms, numerals, electronic
addresses, and multilingual text remains an evidence/policy gap.

| Synthetic input | Word units | Estimated syllables |
| --- | --- | --- |
| `care-based` | 1 | 3 |
| `care/access` | 2 | 1 + 2 |
| `2026` | 1 | 4 |
| `$10` | 1 | 3 |
| `ABC123` | 1 | 1 |
| `résumé` | 1 | 3 |
| `UEI` | 1 | 2 |

These are literal method results, not claims about how a reader pronounces the
input. See [token candidates](../src/hhs_nofo_metrics/methods/token_candidates.py)
and [the shared stream](../src/hhs_nofo_metrics/methods/readability_tokens.py).
Historical v1 helpers are separately exported for legacy consumers; their ASCII
word rules are not the current profiles' word-stream definition.

## Inclusion, exclusion, and recognition

The profile rules are the same across each source's earlier/corrected pair.
The policy acts on **recognized roles**, not on every visual or linguistic
example of a content class.

| Recognized role/content | Document words | All five sentence-based metrics | Provisional rationale and limit |
| --- | --- | --- | --- |
| Body, list, narrative table block | Include words, including fragments | Include accepted sentence text only | Measure selected prose while keeping numerator and denominator aligned |
| Heading | Include | Exclude | Retain content volume without treating a label/title as prose |
| Cover, TOC, navigation | Exclude | Exclude | Avoid counting orientation material as narrative; recognition varies by adapter |
| Header, footer, decorative artifact | Exclude | Exclude | Avoid repeated furniture and non-content marks; misclassification remains possible |
| Instruction | Exclude if this role is actually assigned | Exclude if assigned | Intended to omit author-only directions, not applicant instructions; current adapters do not reliably infer author-only intent |
| Unknown content | HTML: unable if unknown reaches selection; PDF profiles: include with warnings/reliability | Same policy, plus sentence acceptance | Avoid a silent PDF omission; expose uncertainty through sensitivity rather than claim resolved meaning |

The sources of these dispositions are the packaged
[HTML](../src/hhs_nofo_metrics/profiles/hhs-nofo-fy27-html-0.5.0.json),
[tagged PDF](../src/hhs_nofo_metrics/profiles/hhs-nofo-fy27-pdf-estimate-0.6.0.json),
and [generic PDF](../src/hhs_nofo_metrics/profiles/hhs-nofo-fy27-generic-pdf-estimate-0.5.0.json)
profiles. The stated purposes explain the implementation; policy endorsement
and remaining recognition decisions require separate evidence.

### Headings, lists, and tables

HTML recognizes heading tags and `th` as headings, `li` as list content, and
`td` as table content. A complete list/cell sentence can contribute to all
sentence-based metrics; an unpunctuated label still contributes only document
words. Words like "Review" or "Before You Begin" alone do not make ordinary
body/list text navigation or writer instructions.

Tagged PDF maps H/H1–H7 to heading, LBody to list, and **both TH and TD to table**.
Consequently a punctuated TH can contribute sentence words even though the
same text in an HTML `th` is excluded from sentence scope. Released adapter
0.1.7 groups nested cell content under its cell and can lose paragraph/heading
boundaries, particularly across pages. Do not read the profile's exclusion of
heading roles as a guarantee that every table heading has that role. Candidate
0.1.8 improves nested paragraph identities; its
[adoption note](NESTED_TABLE_ADOPTION.md) records the boundaries and pending
producer evidence. It does not change TH into an HTML-equivalent heading rule.

The generic adapter uses line-prefix list patterns and bounded heading-shape
heuristics. It does not reliably reconstruct tables or semantic list structure.
Reflow never joins across pages. A visually wrapped sentence can thus remain
split. These are extraction limits, not alternate formulas.

### TOC, covers, and navigation

Recognized TOC/navigation roles are excluded from **both** scopes in all six
profiles. The following synthetic checks distinguish recognition from policy:

| Input path and representation | D | R | S | P |
| --- | --- | --- | --- | --- |
| HTML `<nav><p>Apply now.</p></nav>` | 0 | 0 | 0 | 0 |
| HTML ordinary `<p>Apply now.</p>` | 2 | 2 | 1 | 1 |
| HTML `<div class="toc"><p>Apply now.</p></div>` | 2 | 2 | 1 | 1 |
| HTML ordinary `<p>Eligibility 3</p>` | 2 | 0 | 0 | 0 |
| Tagged PDF TOCI containing `Apply now.` | 0 | 0 | 0 | 0 |
| Tagged PDF P containing `Apply now.` | 2 | 2 | 1 | 1 |
| Generic PDF line `Eligibility .... 3` | 0 | 0 | 0 | 0 |
| Generic PDF line `Eligibility 3` | 2 | 0 | 0 | 0 |
| Generic PDF line `Apply now.` | 2 | 2 | 1 | 1 |

The generic examples put text on page 2 after a blank first page and keep lines
visually separate, avoiding first-page cover classification and reflow effects.
These are representation-specific examples, not a universal TOC detector.

HTML honors `nav`, `header`, `footer`, hidden/skipped elements, and the caller's
optional `root_id`. A CSS class named `toc` or `cover`, an ordinary heading
"Contents", or dot leaders in a paragraph do not themselves assign a TOC/cover
role. Tagged PDF recognizes TOCI and groups under source-declared TOC or the
supported HHSNofoContents/HHSNofoCover containers. It also has bounded artifact
and standalone-link navigation handling; other producers/custom role maps are
not universally supported. Generic PDF recognizes dot-leader rows ending in a
number and page-number patterns, but also guesses cover content from the first
four otherwise unclassified lines on page 1. That heuristic can omit real body
text or miss cover material.

### Writer instructions, notes, citations, and captions

The role policy expresses an intention to exclude author-only instructions,
but it does not supply a reliable instruction detector. Ordinary HTML such as
`<aside class="instructions"><p>Delete this note.</p></aside>` is body text and
contributes three words and one accepted sentence. Likewise, author directions
converted from Word or tagged as P can remain included. Applicant-facing
instructions remain content. Right-edge panel geometry in tagged PDFs does not
by itself establish writer-only intent or exclude the panel's prose.

Substantive notes versus bibliographic citations are **not reliably separated**
by the current adapters. Tagged Note maps to body; HTML footnote/citation prose
can also be ordinary body text. Terminally punctuated citation text can enter
sentence metrics, while an unpunctuated substantive note can be excluded as a
fragment. "Exclude pure citations" remains a desired distinction requiring
explicit source semantics, validation, and an approved/versioned policy change;
it is not a promise of the current implementation.

Tagged Caption maps to heading and is excluded from sentence scope. HTML
`caption` maps to heading, while `figcaption` maps to body. Thus identical
punctuated caption text can be counted differently. Generic PDF has no reliable
caption/note/citation detector. Intended distinctions based on substantive prose
need further evidence and policy decisions; they are not implemented by reading
the meaning of the text.

### Repeated headers and footers

HTML excludes recognized `header`/`footer` containers, without checking whether
they repeat. Tagged PDF honors Artifact content and has a bounded top-navigation
repair requiring matching artifacts on two other pages. It does not remove all
repeated text by keyword or page position. Generic PDF checks the first/last
line against normalized edge patterns repeated on at least three pages and
30% of pages. It can miss multi-line furniture or mistake repeated real content
for furniture. See [repeated-edge rules](../src/hhs_nofo_metrics/classification/repeated_edges.py).

## PDF uncertainty and source differences

Tagged PDF requires a usable structure tree. Unknown-role text is included in
the primary estimate and excluded in a comparison scenario; metric-specific
reliability reports the sensitivity, unknown-word share, coverage, and page
failures. A low-sensitivity result is not proof that the document was classified
correctly: confidently mislabeled content may not be "unknown" at all.

Generic PDF reconstructs conservative blocks from text-line geometry and caps
reliability at low, even when its include/exclude scenarios agree. There is no
OCR path or automatic recovery of every text box, image, or unsupported object.
Callers must deliberately select the fallback; a tagged-profile failure does
not silently change profiles. See [reliability](../src/hhs_nofo_metrics/estimate_reliability.py)
and [flat-PDF reconstruction](../src/hhs_nofo_metrics/pdf_reflow.py).

Identical resolved content and method identities share the same arithmetic
kernel. Equal formulas alone do not establish cross-system parity when source,
roles, blocks, tokenizer, or accepted sentences differ.

## Passive sentences and Word comparison

Corrected profiles use `hhs-nofo-passive-sentence-rule@0.4.0-provisional`;
earlier profiles retain `0.3.0-provisional`. The bounded classifier looks for
be/get auxiliaries and likely participles, with modifier and adjectival-state
rules. It counts each accepted sentence at most once even when several clauses
are passive. A = 0 with S > 0 legitimately gives 0%; S = 0 gives an unavailable
percentage.

Unambiguous contracted be forms are supported in the corrected method;
ambiguous pronoun `'s` forms retain previous treatment. Reduced passives and
other grammatical cases remain limitations. See
[passive adoption](PASSIVE_V4_ADOPTION.md); the separate
[passive-accuracy investigation](https://github.com/HHS/simpler-grants-pdf-builder/issues/1231)
is outside this documentation work.

Microsoft Word is a calibration baseline, not the product definition. Its
proofing scope, private lexicon, and PDF-to-Word conversion can differ. PassivePy
was a calibration reference, not a runtime dependency or copied implementation.
Neither a successful synthetic check nor shared code establishes Word parity,
HHS approval, document clearance, or a pass/fail outcome.

## Verification and remaining decisions

On October 27, 2026, the published 0.6.0 wheel and sdist hashes were checked
against release metadata. The installed wheel's six profiles, worked example,
token examples, and 22 synthetic HTML/tagged/generic recognition cases were
checked. The same cases were checked against the local 0.6.1 candidate; this
selection documentation does not change calculations. Relevant committed
regressions are in `tests/test_semantic_html.py`, `tests/test_integration.py`,
`tests/test_pdf_reflow.py`, and `tests/test_methods.py`.

Still unresolved: approved rationale for every content class and token edge
case; reliable distinction between writer instructions and applicant prose;
substantive notes versus citations; cross-format caption/table-heading scope;
and evidence sufficient for private real-document or downstream parity claims.
These gaps require sources or separately scoped behavior changes, not stronger
wording in a guide. [Release gates](RELEASE_PROCESS.md) and
[consumer adoption](REUSE_AND_UPDATES.md) remain explicit.
