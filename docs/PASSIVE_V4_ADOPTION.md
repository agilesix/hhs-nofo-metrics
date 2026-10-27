# Passive classifier correction and consumer adoption

Released package: [v0.6.0, October 16, 2026](https://github.com/agilesix/hhs-nofo-metrics/releases/tag/v0.6.0).
Method: `hhs-nofo-passive-sentence-rule@0.4.0-provisional`.
Publication does not establish a consumer's deployed version or formal HHS
approval of the method. [Release gates](RELEASE_PROCESS.md) apply to future
releases; [consumer updates](INTEGRATION_CONTRACT.md#consumer-updates) require
explicit adoption and preservation of earlier results.

## Profile selection

| Source | Historical profile retained | Corrected profile |
| --- | --- | --- |
| Builder HTML | hhs-nofo-fy27-html@0.4.0 | hhs-nofo-fy27-html@0.5.0 |
| Tagged PDF | hhs-nofo-fy27-pdf-estimate@0.5.0 | hhs-nofo-fy27-pdf-estimate@0.6.0 |
| Generic PDF | hhs-nofo-fy27-generic-pdf-estimate@0.4.0 | hhs-nofo-fy27-generic-pdf-estimate@0.5.0 |

The old method module and old profile resources are retained unchanged. The
shared engine selects the classifier declared in the requested profile, including
PDF unknown-content sensitivity calculations. The CLI requires an explicit
profile; it does not automatically select a corrected profile after an install.

## NOFO Builder adoption and verification

NOFO Builder [PR #1123](https://github.com/HHS/simpler-grants-pdf-builder/pull/1123)
adopted the released v0.6.0 wheel and corrected profiles. This is source-level
adoption, not proof of the version used for a particular stakeholder result.
For deployment verification and subsequent upgrades:

1. Verify the released artifact's digest and record its package/profile identities.
   Keep the consumer lockfile aligned with the reviewed artifact.
2. Check `nofos/nofos/readability.py::PROFILE_REFERENCE` for HTML @0.5.0 and both
   PDF profile constants in `nofos/nofos/pdf_readability_worker.py` for the new
   references above. Keep adapter selection aligned with the released package;
   adapter 0.1.7 is already present in 0.5.5 and does not originate in this fix.
3. Verify that the existing snapshot identity checks use both package and profile
   versions. Earlier snapshots stay in history and are not reused as current
   calculations. Existing result schemas and percentage units are unchanged.
4. Test the built-in panel and standalone Word/PDF uploads on appropriate
   synthetic controls, including historical versus corrected profiles. Record
   actual deployed package/profile identity and matching source revisions when
   evaluating a real-document cohort.

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
