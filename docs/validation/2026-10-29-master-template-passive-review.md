# FY27 master-template passive comparison — October 29, 2026

## Decision

Retain the existing passive classification rules. Manual comparison of the
FY27 HHS master template with Windows Microsoft Word did not support adding
exceptions for the three applicant-facing constructions tested. This is a
bounded comparative review, not full Word parity, independent linguistic
validation, formal HHS approval, or completion of the deferred release cohort.

This follow-up to the [definition-modifier evaluation](../PASSIVE_V5_CANDIDATE.md)
used Readability Checker package 0.7.0, HTML profile
`hhs-nofo-fy27-html@0.6.0`, and passive method
`hhs-nofo-passive-sentence-rule@0.5.0-provisional`.
The shared master template is a useful evaluation target because agencies use
it as a starting point; it also contains writer instructions that do not belong
in a finished applicant-facing NOFO.

## Procedure and observations

The contributor performed Word measurements manually and supplied screenshots
and Checker reports. An initial selected-text Word result was discarded; only
whole-document measurements were used. A control-free baseline was established,
and local analysis reproduced the Checker baseline using the released package.
The review then used cumulative edits, comparing each stage with its immediate
predecessor, rather than treating every stage as the original baseline.

| Experiment | Observation | Interpretation |
| --- | --- | --- |
| Remove content controls | Checker recovered-text counts changed while displayed grade and passive percentage remained unchanged | Preserve separate input revisions; control removal alone does not prove identical recovered text |
| Remove two writer-only instruction sentences | Both tools lost two sentences; only Checker displayed a lower passive percentage | Evidence of a possible classification difference, but no exception pursued for guidance removed from finished NOFOs |
| Rewrite a negative guarantee construction into active voice | Both tools displayed lower passive percentages; each retained its own sentence count | No evidence supporting a guarantee exception |
| Rewrite a negative requirement construction into active voice | Both tools displayed lower passive percentages; each retained its own sentence count | No evidence supporting a requirement exception |
| Rewrite a passive deadline list item into active voice | Both tools displayed lower passive percentages; word and sentence counts stayed stable within each tool | No evidence supporting a deadline-fragment exception |

The tools continued to report different sentence totals. A smaller denominator
can produce a higher passive percentage even for the same passive numerator.
The remaining percentage gap therefore does not, by itself, justify another
classifier exception. Word's rounded percentages do not expose its numerator
or establish that its passive denominator is exactly its displayed sentence
count. No exact Word passive inventory or denominator has been verified.

## Reproducible synthetic coverage

[The supporting tests](../../tests/test_passive_comparison_controls.py) use
invented workshop-related examples, not source-document excerpts. Each pair
contains a passive construction and an active rewrite. Public HTML analysis
must retain the independently enumerated two-sentence inventory while changing
the passive numerator from one to zero. Both historical and current HTML
profiles are exercised. A separate synthetic example holds the passive count
fixed while adding active sentences, demonstrating denominator sensitivity.

These tests verify package behavior, not Microsoft Word behavior. They do not
reproduce the real-document comparison or prove that all uses of a participle
have the same grammatical interpretation.

## Evidence and follow-up

Source files, screenshots, per-document reports, and local inventories remain
outside Git under the [public boundary](../PUBLIC_REPOSITORY_BOUNDARY.md).
This record is a sanitized qualitative summary; the contributor's retained
October 29 manual evidence supplies the underlying observations. No Word build
number was recorded, and edited copies were not all independently diffed.

Future comparisons should use the same saved testing copy in both tools,
remove content controls while preserving text, distinguish writer instructions
from applicant-facing content, and record scope and sentence counts alongside
percentages. Do not infer a general Word rule from one rounded percentage.

Pause further exception work unless a larger discrepancy or concrete new
classification example warrants it. If resumed, investigate sentence selection
and boundaries before changing passive rules to force matching percentages.
No runtime, method, profile, schema, package version, release, or consumer
upgrade is required by this record.
