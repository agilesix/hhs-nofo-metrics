# Word upload scope: proposed integration

Tracking: [Builder #1333](https://github.com/HHS/simpler-grants-pdf-builder/issues/1333).
This is design and fixture evidence, not a change to the released checker.

Builder's Word upload worker validates the DOCX and converts it to semantic
HTML. It currently passes only that HTML to the package. Native section
breaks, field boundaries and content-control galleries cannot reliably be
reconstructed from the resulting HTML. Keep the existing validation and
conversion path; do not add a second Word text extractor or trust labels
supplied as arbitrary HTML attributes.

The proposed boundary is to classify source blocks in the package before
conversion, and associate those roles with converted blocks via a
conversion-controlled mechanism. Test the association against the actual
converter, including skipped empty paragraphs, tables, content controls,
field results and split paragraphs. If a role cannot be associated
unambiguously, keep the text countable. Paired bookmarks must surround a
whole HTML block and each occur exactly once.

Use a new, opt-in Word-derived profile with the existing role-based
selection and unchanged formulas. Existing HTML and PDF profiles and prior
results must not change. Report only aggregate excluded word/segment
counts for recognized content. Keep comparison persistence and UI in Builder. The metadata rule requires the
generated Basic information pattern (a "Basic information" or "Before You
Begin" heading) with OpDiv and opportunity number before excluding the three
specific PDF metadata labels.

Single-cell instruction tables must start with a known writer-only label.
Builder reuses its verified template-box eligibility check and passes the
resulting paragraph positions instead of duplicating its DrawingML/VML rules.
A cover is recognized from the Word Cover Pages gallery. Exports that use
plain cover paragraphs (for example, GrantSolutions Announcement Module Word
files) are recognized by position as `cover_position` only when the first
section ends in a section break, is followed directly by a recognized table of
contents (optionally after one label paragraph), has no headings, no line
ending in sentence punctuation, at most 25 words per line and at most 100 words
in total. A section break alone leaves preceding text countable, so opening
applicant prose stays in scope. Tracking:
[#34](https://github.com/agilesix/hhs-nofo-metrics/issues/34). A paragraph that contains both a completed TOC
field result and prose outside the field stays countable, even when it uses
a built-in TOC style.

## Conversion probe

A synthetic DOCX passed through Builder's current Mammoth options preserved
temporary bookmark anchors inside their own HTML paragraphs for a text
paragraph, an otherwise empty paragraph, and a paragraph in a content
control. This supports a conversion-only association prototype. It does
not establish that bookmarks survive all list or field paths. Unmatched
boundaries leave recovered text countable. Markers add no text and the result
does not expose them.
