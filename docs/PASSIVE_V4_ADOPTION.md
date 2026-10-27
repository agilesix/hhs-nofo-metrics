# Passive classifier correction and consumer adoption

Published in [package 0.6.0 on October 16, 2026](https://github.com/agilesix/hhs-nofo-metrics/releases/tag/v0.6.0).
Method: `hhs-nofo-passive-sentence-rule@0.4.0-provisional`.
The release and asset digests were verified on October 27, 2026; see
[installation](INSTALLATION.md). Release notes report package checks and a
private technical cohort. That report is not a new independent cohort run or
proof of a consumer deployment or formal method approval. The current 0.6.1
candidate concerns extraction and is documented separately.

## Profile selection

| Source | Historical profile retained | Corrected profile |
| --- | --- | --- |
| Builder HTML | hhs-nofo-fy27-html@0.4.0 | hhs-nofo-fy27-html@0.5.0 |
| Tagged PDF | hhs-nofo-fy27-pdf-estimate@0.5.0 | hhs-nofo-fy27-pdf-estimate@0.6.0 |
| Generic PDF | hhs-nofo-fy27-generic-pdf-estimate@0.4.0 | hhs-nofo-fy27-generic-pdf-estimate@0.5.0 |

The old method module and old profile resources are retained unchanged. The
shared engine selects the classifier declared in the requested profile, including
PDF unknown-content sensitivity calculations. The API and CLI both require an
explicit profile; select a corrected profile to receive the corrections.
Existing callers selecting the earlier profiles retain their passive method.

## Builder adoption of the published release

1. Use the verified 0.6.0 release artifact and record its wheel SHA-256 and
   commit. The release is published; check the consumer's actual installed
   version rather than assuming deployment follows publication.
2. Pin Builder's dependency and regenerate its lockfile against that artifact.
3. Select HTML @0.5.0 and the PDF references above. Reviewed Builder source at
   `c3fad94` already selects those profiles in `nofos/nofos/readability.py` and
   `nofos/nofos/pdf_readability_worker.py`; a consumer on earlier selections
   must make the change explicitly. Keep adapter selection aligned with the released package;
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

See [release notifications and consumer updates](REUSE_AND_UPDATES.md) for how
to learn about releases, review output impact, lock dependencies, and retain
historical results. Upgrading package code does not automatically select a new
profile or upgrade another system.
