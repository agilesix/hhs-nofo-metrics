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
counts, plus the count attributed to a position-only cover. Keep
comparison persistence and UI in Builder. The metadata rule requires the
generated Basic information pattern with OpDiv and opportunity number before
excluding the three specific PDF metadata labels.

Single-cell instruction tables must start with a known writer-only label.
Builder reuses its verified template-box eligibility check and passes the
resulting paragraph positions instead of duplicating its DrawingML/VML rules.
The position heuristic is deliberately bounded to
front matter with a structural cue immediately following the break and
no earlier structural heading. Unsupported input stays countable.

## Conversion probe

A synthetic DOCX passed through Builder's current Mammoth options preserved
temporary bookmark anchors inside their own HTML paragraphs for a text
paragraph, an otherwise empty paragraph, and a paragraph in a content
control. This supports a conversion-only association prototype. It does
not establish that bookmarks survive all list or field paths. Unmatched
boundaries leave recovered text countable. Markers add no text and the result
does not expose them.
