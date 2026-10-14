# Passive classifier correction and consumer adoption

Candidate package: 0.6.0. Method: `hhs-nofo-passive-sentence-rule@0.4.0-provisional`.
This is a release candidate until the package and private-cohort release gates
in RELEASE_PROCESS.md are complete. No deployment or guidance change is implied.

## Profile selection

| Source | Historical profile retained | Corrected profile |
| --- | --- | --- |
| Builder HTML | hhs-nofo-fy27-html@0.4.0 | hhs-nofo-fy27-html@0.5.0 |
| Tagged PDF | hhs-nofo-fy27-pdf-estimate@0.5.0 | hhs-nofo-fy27-pdf-estimate@0.6.0 |
| Generic PDF | hhs-nofo-fy27-generic-pdf-estimate@0.4.0 | hhs-nofo-fy27-generic-pdf-estimate@0.5.0 |

The old method module and old profile resources are retained unchanged. The
shared engine selects the classifier declared in the requested profile, including
PDF unknown-content sensitivity calculations. CLI defaults are retained;
explicitly select a corrected profile to receive the corrections.

## Builder adoption after package review and release

1. Publish the reviewed release artifact after the release gates pass. Record
   its wheel SHA-256 and commit. Do not point Builder at an unpublished release URL.
2. Pin Builder's dependency and regenerate its lockfile against that artifact.
3. Update `nofos/nofos/readability.py::PROFILE_REFERENCE` to HTML @0.5.0 and both
   PDF profile constants in `nofos/nofos/pdf_readability_worker.py` to the new
   references above. Keep adapter selection aligned with the released package;
   adapter 0.1.7 is already present in 0.5.5 and does not originate in this fix.
4. Verify that the existing snapshot identity checks use both package and profile
   versions. Earlier snapshots stay in history and are not reused as current
   calculations. Existing result schemas and percentage units are unchanged.
5. Test the built-in panel and authenticated PDF upload with identical synthetic
   text, including historical versus corrected profiles. Record actual deployed
   package/profile identity when evaluating a real-document cohort.

## Measurement interpretation

The corrections can raise or lower passive percentages. They do not change the
sentence denominator, count multiple passive clauses more than once, alter other
metric formulas, or change any configured target. Remaining classifier limits,
PDF extraction differences and source-scope differences require separate review.
The Word/PDF calibration study needs matching source versions and raw results.

Ambiguous pronoun `'s` retains previous behavior, because by-phrases also appear
in active perfects such as "She's traveled by train" and "It's required, by my
estimate, two hours of work." Thus "It's required by the agency" remains a known
miss requiring stronger grammatical disambiguation. Explicit `been` and `being`
passives work without expanding `'s`. This release addresses the unambiguous
contraction and non-participle cases in issue #10; it does not close that issue's
remaining ambiguous-contraction case.
