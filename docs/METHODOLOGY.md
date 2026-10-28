# Measurement methodology

Status: **provisional implementation; not formally HHS-approved**

## In brief

<!-- Keep this section and README.md#how-the-metrics-are-calculated accurate
when content selection, sentence rules, formulas, input handling, or reliability
changes. Check methods/, adapters/, profiles/, metric_scopes.py,
resolved_scope.py, and semantic_html_engine.py under src/hhs_nofo_metrics/.
Also re-check the HHS/Builder section when guidance or consumer behavior changes. -->

**The aim is to measure content intended for applicants.** Navigation, covers,
tables of contents, headers, footers, decorative material, and instructions
intended only for NOFO writers are excluded when the file's structure identifies
them.

The package cannot reliably recognize all of this content by appearance alone.
For example, a table of contents identified as navigation can be excluded, but
the same text stored as ordinary paragraphs may count. These readability metrics
can help authors review their NOFO when preparing the NOFO submission package
for Departmental review. They do not determine whether a NOFO is clear,
accessible, or ready for submission.

**The readability metrics describe different aspects of the text.** Word Count
reports how much selected text the NOFO contains. Average words per sentence
and characters per word describe sentence and word length. Flesch Reading Ease
and Flesch-Kincaid Grade Level combine sentence length and estimated syllable
counts to indicate reading difficulty. Passive-sentence percentage reports how
often the package recognizes passive voice. These are signals for people to
review, not judgments about every sentence or proof of reader comprehension.

**Word Count includes more text than the other readability metrics.** It
includes selected headings, labels, paragraphs, lists, table text, and text
fragments. The other five readability metrics use the same selected text from
paragraphs, lists, and table cells. That text must end with a period, question
mark, or exclamation point. Headings are left out of those five readability
metrics.

For example, "Submit your application by Friday." can contribute to all five
readability metrics. "Application deadline" can contribute to Word Count but
is left out of the other readability metrics because it has no ending
punctuation. A heading identified as a heading also counts toward Word Count
but is left out of the other readability metrics, even if it ends with a period.

The package accounts for some punctuation that does not end a sentence, such as
periods in recognized abbreviations, decimals, and web addresses. It does not
check whether a sentence is grammatically complete. A fragment ending with a
period can still count. See [content selection and its limits](#content-selection-and-rationale)
for the detailed rules.

A candidate passive rule treats “as defined by” as a reduced definition modifier,
rather than evidence on its own of a passive sentence. Another passive clause
in the same sentence still counts. Released 0.7.0 adds opt-in
profiles for this method; historical profiles retain their released rules.
See the [method evaluation](PASSIVE_V5_CANDIDATE.md).

**How a Word or PDF file identifies its content affects what gets counted.**
For example, a heading identified as a heading is treated differently from text
that only looks like a heading. A PDF without structural tags can make reading
order harder to identify on pages with multiple columns, in tables, or around
sidebars and text boxes.

- **Word content imported into NOFO Builder:** this package does not read Word
  files directly. Builder imports the content, saves it, and renders it as
  HTML—the format used for web pages. The package uses the identified headings,
  paragraphs, lists, and tables in that HTML to calculate readability metrics.
  Importing or rendering the content differently can change the results.
- **PDF with structural tags:** tags identify content such as paragraphs and
  tables. The package uses those tags to interpret the document and reports how
  reliable its estimates are. Missing or incorrect tags can change the counts
  even when the PDF looks correct.
- **PDF without usable structural tags:** the package estimates paragraphs and
  reading order from the placement of text on the page. Repeated headers and
  similar material may remain included. These results are reported as
  low-reliability estimates.

**Results can differ from Microsoft Word's readability statistics.** Word uses
its own rules for counting words and sentences, estimating syllables, and
identifying passive voice. This package uses its own documented, versioned
rules. The two may also include different content because of headings,
paragraph boundaries, or changes introduced during conversion. Matching Word's
numbers is not the package's definition of correctness. Readability metrics
help people review writing; they do not demonstrate that readers will
understand it.

## HHS Departmental review and NOFO Builder

These readability metrics can help authors review their NOFO when preparing
the NOFO submission package for Departmental review. The package calculates
readability metrics; it does not determine whether submission requirements
have been met.

For submission instructions, follow the *HHS FY 2027 NOFO Content and Clearance
Guidance*, including **Step 2. Submit your NOFO for Departmental clearance**.
Use that guidance for requirements about the final designed PDF, approved
Office of Grants tools, and submission materials.

The SimplerNOFOs team supports reviewing readability metrics through NOFO
Builder's **Readability metrics** panel and the **Readability Checker**, which
checks uploaded documents. Access and supported file formats depend on the
tool's availability and your permissions. Follow the FY27 guidance for
calculating and submitting readability metrics for Departmental review.

Builder's panel calculates readability metrics from the NOFO's saved content.
The [Builder guide](consumers/NOFO_BUILDER.md) describes the calculation path
and technical details. This overview does not establish that a particular tool
or calculation path is approved for Departmental submissions.

## About this document

This describes the whole-NOFO calculations implemented by the bundled profiles,
not a new calculation policy. The HHS Office of Grants directs the work and
measurement decisions; Agile Six implements and maintains the code as a
contractor. This does not establish legal ownership of code or change its
[license](../LICENSE).

Each result identifies its package, profile, methods, adapter and input. Those
versioned contracts define what was calculated. See the
[integration contract](INTEGRATION_CONTRACT.md) for API/CLI entrypoints, result
fields and consumer responsibilities.

## Measurement scopes

The package calculates one result for the supplied content scope. Consumers
must supply the whole NOFO, not average section-level scores: ratios and Flesch
formulas calculated from aggregate counts need not equal an average of sections.

Two independent scopes serve different purposes:

1. **Document content** supplies standalone Word Count. Selected headings,
   labels, list items, table content and fragments can contribute words even
   when they do not form a sentence. This measures the amount of selected text.
2. **Readability sentences** supply the other five metrics. Only tokens in
   accepted sentence candidates contribute. This keeps a heading or fragment
   from increasing a numerator without increasing the sentence denominator.

Every sentence-scoped metric reuses the same accepted inventory. "Accepted"
means the boundary rules found terminal `.`, `!` or `?`, with protection for
recognized abbreviations, decimals and URLs. It is not a grammatical-completeness
test: a punctuated fragment can pass, while an unterminated instruction can be
excluded. Separate semantic blocks are not joined to manufacture a sentence.

## Content selection and rationale

The provisional purpose is to measure applicant-facing content while limiting
the effect of navigation, layout furniture and writer-only instructions.
Profiles select **normalized roles**; adapters must first recognize those roles.
This is implemented behavior, not a claim that every format reliably identifies
each content category.

| Content represented by recognized roles | Document words | Sentence metrics | Reason |
| --- | --- | --- | --- |
| Body prose, list items and table cells | Include | Include accepted sentences only | Count selected text without treating every fragment as a sentence |
| Headings and heading-like labels | Include | Exclude | Account for length without distorting sentence ratios |
| Cover, TOC, navigation, header, footer, decorative or writer-instruction roles | Exclude | Exclude | Keep recognized non-body material outside scope |
| Unknown role | HTML cannot calculate if unknown segments occur; PDF estimates include with sensitivity reporting | Same role policy, then sentence selection | Expose uncertainty about structure |

Recognition depends on the input path:

- **HTML** uses DOM order and element boundaries. `<nav>`, `<header>` and
  `<footer>` establish excluded roles, including for descendants. Heading tags,
  `<th>`, `<caption>`, `<dt>`, `<legend>` and `<summary>` become headings;
  `<li>` establishes list content and `<td>` table content. Ordinary paragraphs
  are body content unless nested in another recognized context. Hidden elements
  and non-content elements such as scripts are skipped. The adapter does not
  infer covers, writer instructions, citations or TOCs from visual styling,
  arbitrary CSS class names or arbitrary `role` attributes.
- **Tagged PDFs** use source-declared structure and selected producer/profile
  rules. For example, `TOCI` maps to table of contents, `Note` to body and
  `Caption` to heading. Unknown content contributes to estimates, with coverage
  and include/exclude-unknown sensitivity reported. A tag is evidence of source
  structure, not proof that the producer assigned the right meaning.
- **Generic PDFs** reconstruct conservative blocks from visual text lines.
  Without reliable semantic roles, their metrics remain low-reliability
  estimates. Do not assume every repeated header, footer or TOC row is removed.

Common cases illustrate the limits:

- A TOC inside HTML `<nav>` is excluded from **both** scopes. The same text in
  ordinary paragraphs can add document words and, if punctuated, accepted
  sentences. An unpunctuated TOC row can add words without a sentence. Tagged-PDF
  `TOCI` is excluded, but a visually identical unrecognized PDF row need not be.
  There is no universal TOC-removal guarantee.
- An accepted instruction in a list or table cell contributes to sentence
  metrics; an unpunctuated fragment contributes only document words. A `<th>`
  is a heading, while an ordinary `<td>` label is not automatically recognized
  as a label.
- Substantive footnotes/endnotes may be applicant-facing prose; pure citations
  are not the intended sentence-reading target. Neither the HTML adapter nor a
  PDF `Note` tag automatically distinguishes them. A punctuated citation
  represented as body content can count. HTML `<caption>` and PDF `Caption`
  are headings even when substantive; HTML `<figcaption>` ordinarily remains
  body content.
- Writer instructions and covers are excluded only when supplied scope or
  recognized structure separates them. Text that merely looks like a cover or
  instruction can count as body content. Consumers that prepare a narrower HTML
  scope must record that preparation for reproducibility.

Retain adapter/input provenance and test the real consumer path. These limits
are not new automatic exclusion rules.

## Metric definitions

Let `W` be word units in accepted sentences, `S` accepted sentences, `C` their
characters, `Y` their syllables and `P` sentences classified passive. Standalone
Word Count uses its own selected inventory, not `W`.

| Metric | Definition | Purpose and limit |
| --- | --- | --- |
| Word Count | Word units in selected document content | Selected text volume, not reading difficulty |
| Average words per sentence | `W / S` | Sentence-length signal; does not measure clarity or grammatical complexity |
| Characters per word | `C / W` | Word-length signal; does not determine whether a term is familiar |
| Flesch Reading Ease | `206.835 - 1.015 × W/S - 84.6 × Y/W` | Higher scores suggest easier reading under this sentence/syllable formula, not demonstrated comprehension |
| Flesch-Kincaid Grade Level | `0.39 × W/S + 11.8 × Y/W - 15.59` | Expresses those length signals on an estimated US school-grade scale, not a required reader qualification |
| Passive sentences (%) | `100 × P/S` | Frequency of recognized passive constructions, not a judgment that every passive is inappropriate |

Sentence-metric components also include sentence-bearing paragraph/block count
and `sentences_per_paragraph = S / paragraph_count`. These are logical blocks
after source resolution, not rendered lines. This is not a seventh top-level metric.

Arithmetic uses unrounded components. The engine publishes sentence-metric
values rounded to two decimal places and retains `unrounded_value`; standalone
Word Count is an integer. Consumer display bands and further rounding are
presentation decisions. An unusable denominator produces `unable_to_calculate`,
not fabricated zero. A measured zero, such as no passive sentences in a usable
inventory, is valid.

## Word, character and syllable units

Current profiles share `word-readability-character-token-candidate@0.1.0`.
It starts from whitespace chunks, splits bounded separators including
URL/slash boundaries and en/em dashes, ignores bullet/check markers, and
normalizes bounded edge punctuation while preserving supported abbreviations
and numeric outlines. Character count sums the resulting token surface lengths,
not all raw document characters or whitespace. See the exact
[token rules](../src/hhs_nofo_metrics/methods/token_candidates.py).

Syllables use `word-syllable-candidate@0.1.0`: dictionary exceptions plus a
Unicode-normalized vowel-group heuristic, with bounded treatment of numbers,
mixed identifiers, URLs and email addresses. This is a reproducible estimate,
not a dictionary lookup for every English or technical term. See the
[readability token methods](../src/hhs_nofo_metrics/methods/readability_tokens.py).

## Passive sentences

Released v0.6.0 includes corrected profiles: HTML `0.5.0`, tagged PDF estimate
`0.6.0` and generic PDF estimate `0.5.0`. They use
`hhs-nofo-passive-sentence-rule@0.4.0-provisional`; historical profiles retain
`0.3.0-provisional` unchanged. Installing a release does not select a profile
or upgrade a deployed consumer. See [adoption notes](PASSIVE_V4_ADOPTION.md).

The deterministic classifier recognizes a form of `be` or `get` followed by a
likely past participle, with bounded intervening modifiers. It includes explicit
irregular participles and excludes bounded adjectival-state and existential
noun-modifier patterns. A sentence counts once if any recognized passive occurs.
Broader reduced passives are outside the current rule.

The corrected method recognizes contracted be auxiliaries, excludes `need` and
`indeed` as participles, and accepts `indeed` as an intervening modifier.
Ambiguous pronoun `'s` retains previous behavior because it can mean either
`is` or `has`. PassivePy was an attributed calibration reference, not a runtime
dependency; its code is not copied into this package.

Released `hhs-nofo-passive-sentence-rule@0.5.0-provisional`
skips `defined` only in the existing `as + participle + by` scan. It retains
finite be/get passives, including “The award is defined by the agreement,” and
other reduced by-phrases. It does not use agency names, lists of statutes, or a
sentence-wide string exemption. It does not determine grammatical completeness
or limit the modifier exception to legal citations. Released 0.7.0
selects it in HTML profile `0.6.0`, tagged-PDF
profile `0.7.0` and generic-PDF profile `0.6.0`. Historical profiles remain
unchanged. Denominators and other metric formulas are unchanged for a fixed
inventory; the release also includes a separately versioned tagged-adapter
repair, which can change PDF extraction scope. See
[candidate evaluation](PASSIVE_V5_CANDIDATE.md).

## Reuse, comparison and change control

HTML is preferred when the consumer owns ordered content. Supported paths
converge on the same calculation kernel after source-specific resolution, but
this does not guarantee equal inventories or values across formats. DOCX is
not a built-in core input: Builder's Word-to-HTML conversion and import
transforms remain consumer-side adapters. Record their revisions with the
package/profile/input identities when comparing reports.

Microsoft Word is a calibration baseline, not the product definition. Its
proofing scope, private lexicon and PDF-to-Word conversion can produce different
totals. These results do not assert Word parity, passive classifier accuracy
or clearance/accessibility approval.

Output-changing policy requires a new immutable profile or method version
and regression tests. Existing results retain original identities and values;
recalculate explicitly under a named new profile rather than rewriting history.
Follow [consumer update steps](INTEGRATION_CONTRACT.md#consumer-updates) for
release notifications, verified artifact pins, regression checks and deliberate
adoption. Future HHS decisions about token edge cases, presentation bands and
uncertainty wording remain distinct from this provisional implementation.

## Nested table paragraph repair candidate

The nested-table repair initially prepared for 0.6.1 is included in the
released package 0.7.0, with tagged adapter 0.1.8 / resolver
0.3.8. It preserves the identity of a declared paragraph inside a TD/TH across
pages, while keeping separate paragraphs, headings, and cells separate. This
can change accepted sentence words and sentence-bearing block counts under an
existing profile; formulas and released profiles are unchanged. Published 0.6.0
retains adapter 0.1.7 and its page-local nested-cell limitation. See
[nested table adoption](NESTED_TABLE_ADOPTION.md) for supported structures,
independent synthetic references, remaining producer limitations, and pending
Word-export, release, and Builder verification. A nested PDF table heading
retains its existing table role; this repair does not make its scope equivalent
to an HTML `th`.
