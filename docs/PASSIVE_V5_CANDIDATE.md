# Definition modifier passive candidate

The candidate method `hhs-nofo-passive-sentence-rule@0.5.0-provisional` stops
counting the reduced modifier “as defined by” alone as evidence of a passive
sentence. The intent is to distinguish a reference to a definition from a finite
passive predicate. This is a provisional measurement choice, not a declaration
that reduced clauses have no passive grammatical interpretation.

## Exact behavior

The candidate copies the released 0.4 method and changes only its reduced
`as + participle + by` scan: the candidate participle `defined` is skipped.
The finite be/get scan runs unchanged, and other reduced by-phrases remain
eligible. Case normalization and existing bounded intervening-modifier handling
are preserved. There are no agency, organization or statutory-citation lists.

The exception applies to the modifier within fragments and otherwise complete
sentences, including imperatives. It is not a grammatical-fragment detector or
a legal-reference recognizer. A sentence is never excluded wholesale merely
because it contains the phrase.

These examples are invented:

| Text | Released method 0.4 | Candidate 0.5 |
| --- | --- | --- |
| An eligible organization as defined by the charter. | Passive | Not passive |
| Community associations, as defined by the program handbook. | Passive | Not passive |
| Use the method as defined by the handbook. | Passive | Not passive |
| The award is defined by the agreement. | Passive | Passive |
| An entity as defined by the charter is selected annually. | Passive | Passive |
| Use the process as defined by the charter and as approved by the board. | Passive | Passive |
| The board reviews applications. | Not passive | Not passive |

Changing this classification does not remove words or sentences from metric
scope. The passive numerator can decrease; the sentence denominator, word and
syllable counts, grade and other formulas stay unchanged for a fixed inventory.

## Evaluation without activating a profile

No packaged profile references this method. The public `analyze` API and CLI
continue to select released behavior. For explicit kernel evaluation with
synthetic inputs:

```python
from hhs_nofo_metrics.methods.passive_voice_v5 import METHOD_REFERENCE
from hhs_nofo_metrics.resolved_scope import (
    ResolvedMeasurementScope,
    calculate_resolved_measurement_scope,
)

sentences = (
    "An eligible organization as defined by the charter.",
    "Applications are reviewed by the board.",
)
scope = ResolvedMeasurementScope(
    document_status="eligible",
    readability_status="eligible",
    document_content_units=sentences,
    readability_sentences=sentences,
)
result = calculate_resolved_measurement_scope(
    scope,
    classify_passive_voice=True,
    passive_method_reference=METHOD_REFERENCE,
)
assert result.readability_counts.passive_sentence_count == 1
assert result.readability_counts.sentence_count == 2
```

This uses an internal evaluation interface, not a newly supported public
profile. Adoption needs a separately versioned profile, package release and
explicit consumer selection. Do not relabel old results with the candidate
identity or assume installing a package activates it.

## Validation and remaining decisions

`tests/test_passive_v5.py` covers definition modifiers, mixed case, intervening
modifiers, finite definitions, genuine be/get passives before and after the
modifier, contractions, another reduced passive later in the sentence, active
controls, counting a sentence once, and preservation of the accepted inventory
and other metric values. Historical profile selection remains unchanged.

An independently enumerated six-item synthetic inventory contains three
standalone definition modifiers, two genuinely passive sentences and one active
sentence. The released method counts five passive items; the candidate counts
two, with all six sentences retained. These are synthetic expectations, not
Microsoft Word parity or human linguistic validation.

Local checks on October 28, 2026: 33 candidate regressions and the full 363-test
suite passed, with 86.22% overall coverage against the 84% requirement. Formatting,
lint, pre-commit, public-boundary and release-identity checks passed. These checks
establish tested implementation behavior, not independent linguistic validation.

Private-document cohort validation and independent method review remain pending.
Only use eligible inputs and approved workflows under the
[public repository boundary](PUBLIC_REPOSITORY_BOUNDARY.md). Keep private source
files and per-document evidence out of this repository. If adopted, select new
profiles explicitly and validate each consumer's conversion path separately.
Do not bundle this candidate into a release merely because it shares a working
package version with another unreleased correction.
