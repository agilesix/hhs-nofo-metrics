# Definition modifier passive rule

The released provisional method `hhs-nofo-passive-sentence-rule@0.5.0-provisional` stops
counting the reduced modifier “as defined by” alone as evidence of a passive
sentence. The intent is to distinguish a reference to a definition from a finite
passive predicate. This is a provisional measurement choice, not a declaration
that reduced clauses have no passive grammatical interpretation.

## Investigation and rationale

Manual comparison with Microsoft Word separated two possible sources of different
passive percentages: different text being measured, and different passive
classifications within that text. Small wording substitutions and a separate
content-control removal test were used to investigate them.

Replacing definition modifiers reduced the Checker's passive count without
changing its sentence count, while Word's displayed passive percentage stayed
unchanged. Separately, bulk removal of Word content controls increased Word's
measured sentence count to match the Checker's count, but a passive-percentage
difference remained. These observations support keeping scope and classification
investigations separate. Equal sentence totals do not establish identical
sentence inventories or a shared classifier.

This candidate addresses the definition-modifier classification only. It does
not repair Word proofing scope or explain every remaining discrepancy. Matching
Word is not itself a correctness criterion. The question for method review is
whether treating a reduced definition modifier alone as passive evidence gives
useful feedback while preserving recognition of other passive clauses.

Document-specific observations and source evidence remain private. The examples
and fixtures here are invented. The manual observations motivated this candidate;
they are not a completed cohort evaluation of the implemented method.

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

## Profile selection in release 070

Released 0.7.0 makes the method selectable through the public
analysis API and CLI. These profiles remain provisional:

| Input | Existing profile retained | New opt-in profile |
| --- | --- | --- |
| Semantic HTML including consumer-converted Word | `hhs-nofo-fy27-html@0.5.0` | `hhs-nofo-fy27-html@0.6.0` |
| Tagged PDF | `hhs-nofo-fy27-pdf-estimate@0.6.0` | `hhs-nofo-fy27-pdf-estimate@0.7.0` |
| Untagged PDF | `hhs-nofo-fy27-generic-pdf-estimate@0.5.0` | `hhs-nofo-fy27-generic-pdf-estimate@0.6.0` |

```python
from hhs_nofo_metrics import SourceBundle, analyze

source = SourceBundle.from_html(
    b"<p>An eligible entity as defined by the charter.</p>"
    b"<p>Applications are reviewed by the board.</p>"
)
result = analyze(source, profile="hhs-nofo-fy27-html@0.6.0")
assert result.metrics["passive_sentence_percentage"].value == 50
assert result.metrics["words_per_sentence"].components["sentence_count"] == 2
```

The earlier PR #25 exposed only an explicit kernel candidate; release 0.7.0
adds profiles and engine validation for the public paths. Installing the package
does not change a caller's selected profile. Keep old results under their actual
identities and recalculate explicitly. Package publication is complete; downstream adoption is separate. The
[release record](RELEASE_0_7_0.md) discloses the release-specific validation deferral.

## Validation and remaining decisions

`tests/test_passive_v5.py` covers definition modifiers, mixed case, intervening
modifiers, finite definitions, genuine be/get passives before and after the
modifier, contractions, another reduced passive later in the sentence, active
controls, counting a sentence once, and preservation of the accepted inventory
and other metric values. Historical profiles retain their selected methods.
`tests/test_passive_v5_profiles.py` also exercises public API selection for HTML,
tagged PDF and generic PDF, plus fixed inventories, source-free results and
profile changes limited to identity, description and passive method.

An independently enumerated six-item synthetic inventory contains three
standalone definition modifiers, two genuinely passive sentences and one active
sentence. The released method counts five passive items; the candidate counts
two, with all six sentences retained. These are synthetic expectations, not
Microsoft Word parity or human linguistic validation.

Local checks on October 28, 2026: 33 candidate regressions and the full 363-test
suite passed, with 86.22% overall coverage against the 84% requirement. Formatting,
lint, pre-commit, public-boundary and release-identity checks passed. These checks
establish tested implementation behavior, not independent linguistic validation.

The broader real-document cohort gate was deferred for 0.7.0 by explicit release
decision, as recorded in [the release record](RELEASE_0_7_0.md). Independent
linguistic validation and downstream consumer verification remain pending.
Only use eligible inputs and approved workflows under the
[public repository boundary](PUBLIC_REPOSITORY_BOUNDARY.md). Keep private source
files and per-document evidence out of this repository. If adopted, select new
profiles explicitly and validate each consumer's conversion path separately.
Do not bundle this candidate into a release merely because it shares a working
package version with another unreleased correction.
