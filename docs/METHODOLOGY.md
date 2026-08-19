# Measurement methodology

Status: **provisional implementation; not HHS-approved**

This document is the human-readable specification for the measurement policy
implemented by the bundled HHS NOFO profiles. Immutable profile and method
identifiers in each result remain the machine-readable authority.

## Measurement scopes

The package resolves two independent scopes:

1. **Document content** supplies standalone Word Count. It can include selected
   headings, labels, list items, table content, and applicant-facing fragments.
2. **Readability sentences** supply average words per sentence, characters per
   word, both Flesch metrics, and passive-sentence percentage. Only words in
   complete accepted sentences enter this scope.

This separation prevents structural fragments from increasing a readability
numerator without increasing its sentence denominator.

## Metric definitions

| Metric | Definition |
| --- | --- |
| Word Count | Word units in selected document content |
| Average words per sentence | Readability words divided by accepted sentences |
| Characters per word | Readability characters divided by readability words |
| Flesch Reading Ease | `206.835 - 1.015 × words/sentence - 84.6 × syllables/word` |
| Flesch-Kincaid Grade Level | `0.39 × words/sentence + 11.8 × syllables/word - 15.59` |
| Passive sentences | Sentences classified passive divided by accepted sentences |

Arithmetic uses unrounded components. Display rounding and preferred bands are
presentation policy. An unusable denominator produces `unable_to_calculate`,
not numeric zero.

## Sentence selection

| Content class | Default disposition |
| --- | --- |
| Complete applicant-facing body sentence | Include |
| Heading, section title, label, or navigation text | Exclude |
| Unterminated prose or list fragment | Exclude |
| Complete bullet, numbered item, or checklist instruction | Include |
| Table header or key/value label | Exclude |
| Complete applicant-facing sentence in a narrative table cell | Include |
| Bibliographic citation or reference entry | Exclude |
| Substantive applicant-facing footnote or endnote sentence | Include |
| Pure citation footnote or endnote | Exclude |
| Caption or figure note | Include only when it contains substantive prose |
| Repeated header, footer, page number, or table-of-contents row | Exclude |
| Sentence split only by supported layout reconstruction | Include once |
| Ambiguous denominator-changing boundary | Treat according to the selected profile's reliability contract |

A label followed by a complete instruction contributes the instruction, not
the label. Text from separate source blocks is not joined merely to manufacture
a sentence. Every sentence-scoped metric reuses the same accepted inventory.

## Source behavior

Semantic HTML uses DOM order and semantic element boundaries. It is the
preferred source when the content system owns ordered HTML.

Tagged PDFs use source-declared structure groups. Unknown roles are handled by
the selected profile and remain visible through coverage, reliability, and
sensitivity fields.

Generic PDFs reconstruct conservative paragraph blocks from visual text lines.
That path is useful when no better source exists, but its metrics are always
reported as low-reliability estimates.

All paths converge on the same internal token, character, syllable,
readability, and passive-voice kernel after source-specific resolution.

## Passive sentences

The current provisional classifier recognizes a form of `be` or `get` followed
by a likely past participle, with bounded intervening modifiers. It includes
explicit irregular participles and excludes bounded adjectival-state and
existential noun-modifier patterns. Broader reduced passives are outside the
current rule.

The classifier is deterministic and independently versioned. It does not claim
to reproduce Microsoft Word's private grammar checker. PassivePy was used as
an attributed calibration reference; it is not a runtime dependency and its
code is not copied into this package.

## Relationship to Microsoft Word

Microsoft Word is a calibration baseline, not the product definition. Its
proofing scope, private lexicon, and PDF-to-Word conversion can produce
different sentence and syllable totals. This package prioritizes a transparent,
versioned, reproducible method over undocumented Word compatibility.

## Approval and change control

The initial HHS policy still requires approval or revision of token edge cases,
character and syllable treatment, display bands, and passive-voice uncertainty
language. A policy change that can alter output requires a new immutable
profile or method version and focused regression tests; a released contract is
never edited in place.
