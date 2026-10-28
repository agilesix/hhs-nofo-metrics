# Release 0.7.0 preparation

Status: **authorized for publication after automated gates**. Planned date: October 28, 2026.
The planned date and dated changelog must be refreshed if publication happens later.

## Scope and authorization

Ben explicitly requested the release-preparation PR and publication of 0.7.0,
including making the new passive method selectable, and directed proceeding
without asking Mike for separate agreement. This is the release-specific scope
and publication authorization. It does not establish formal HHS method approval
or waive the repository's validation and public-information gates.

Base: `bee45e54864093f1a375f2ded2f3239e4562d301` on `main`.
This release includes all merged changes since published tag `v0.6.0`:

| Included work | Release impact |
| --- | --- |
| PR #25 and this preparation | Definition-modifier passive method 0.5; new selectable profiles and public-path support |
| PR #14 | Nested tagged-table paragraph continuity, adapter 0.1.8 / resolver 0.3.8; initially prepared as unpublished 0.6.1 |
| PR #15 | Consumer/reuse and maintenance guidance |
| PR #16 | README and getting-started documentation organization |
| PRs #17, #18 and #19 | AI contribution, repository access and governance guidance |
| PRs #21, #22 and #23 | Plain-language methodology and final Checker naming/link presentation |

No additional open PR is a declared dependency. The nested-table correction is
included because it is already merged into the chosen source baseline; it is
not silently treated as a separately published 0.6.1. Its distinct unsupported
Word-export object case remains documented in
[nested-table adoption](NESTED_TABLE_ADOPTION.md#word-export-observation).
The release does not claim to repair that case or every PDF paragraph boundary.

## Measurement contracts

Package and fallback version: **0.7.0**. New profiles:

| Input | New profile | Passive method |
| --- | --- | --- |
| Semantic HTML | `hhs-nofo-fy27-html@0.6.0` | `0.5.0-provisional` |
| Tagged PDF | `hhs-nofo-fy27-pdf-estimate@0.7.0` | `0.5.0-provisional` |
| Generic PDF | `hhs-nofo-fy27-generic-pdf-estimate@0.6.0` | `0.5.0-provisional` |

All six previously packaged profiles and released methods remain available.
New profiles change only identity, description and passive method relative to
the immediately preceding profiles. The definition-modifier rule can change
the passive numerator, while preserving a fixed resolved inventory and other
metric calculations. The separate tagged-adapter repair can change recovered
PDF scope and therefore other metric values; an unchanged profile does not
make extraction changes disappear. Preserve the full original package/adapter
identity when reproducing historical reports.

API and CLI shapes and result schema identities are retained. Callers must
explicitly select the new profiles; installing the package is insufficient to
activate the definition-modifier option in an existing consumer.

## Verification and publication gates

Synthetic expectations are specified independently of the parser output:

- The classifier fixture retains six accepted items: three definition modifiers,
  two genuinely passive sentences and one active sentence. The passive count
  changes from five to two; the accepted scope does not change.
- Public HTML, tagged-PDF and generic-PDF fixtures each contain four sentences:
  one definition modifier, one finite passive, one modifier plus a finite passive,
  and one active. Only the modifier-alone match changes; passive count changes
  from three to two, with all four sentences retained and other metrics equal.
- Existing nested-table tests check text, source-declared block identity,
  page provenance, denominators and metrics against literal synthetic references.

Local preparation checks passed: **369 tests**, **86.22% coverage**, formatting,
lint, pre-commit, public tree/history boundary, tagged release identity, and
wheel/source-distribution contents plus clean-install API/CLI checks. The new
profile paths were exercised on invented inputs. GitHub CI and final release
artifact receipts are recorded in the release PR as they complete. Checks must be rerun on the final release commit and artifact.
A previous package build or a green PR is not the hosted tag check.

## Release decision and deferred validation

On October 28, 2026, Ben explicitly directed proceeding with 0.7.0 without the
broader five-source real-document gate for this release. The decision accepts
the bounded scope on the basis of the manual investigation summarized in
[PR #25](https://github.com/agilesix/hhs-nofo-metrics/pull/25),
its synthetic regression evidence, and this preparation's public-path and
package checks. This is a release-specific exception, not a change to the
default gate for future releases. No further Mike agreement was requested.

The investigation found that definition-modifier substitutions changed Checker
passive classification with a fixed Checker sentence denominator, while Word's
displayed passive percentage stayed unchanged. A separate bulk content-control
removal test changed Word's measured scope and brought sentence counts into
agreement, while a passive-percentage difference remained. The evidence supports
separating scope and classifier issues; it does not establish Word parity,
independent linguistic accuracy, or that this candidate resolves every difference.
Only the sanitized explanation is public; source documents and per-document
receipts are not part of the release.

The five-source gate remains **not run for 0.7.0**: Builder HTML, native
Builder/Prince PDF, Builder Word-to-PDF, non-Builder tagged PDF and
untagged/degraded PDF were not evaluated as a frozen release cohort. Synthetic
checks are not relabeled as real-document evidence. Independent linguistic
validation and downstream consumer verification also remain unestablished.
The existing nested-table producer limitation remains accepted as outside the
bounded repair; the release does not claim it fixed.

Ben's explicit publication instruction is the release decision. The existing MIT
attribution is unchanged, and source/examples added for this release are invented.
No pre-decisional documents or derivatives have been included. Automated scans
still do not establish formal policy or public-release approval.

## Publication sequence

1. Retain the release-specific real-document deferral above and the known limits;
   complete all automated gates and retain the unchanged license attribution.
2. Merge this release preparation with required checks passing. Freeze the exact
   merge commit, refresh the date as needed, and build/check both distributions
   from the final committed source. Verify clean-install API and CLI behavior,
   TOON/JSON output, all profile resources and the new passive classification.
3. Validate identity using `python tools/check_release_identity.py --tag v0.7.0`.
   Create and push the single annotated tag on the reviewed commit. Wait for
   hosted tag CI, including package/boundary checks and the secret scan.
4. Publish a GitHub Release only after those gates pass. Include the reviewed
   wheel and source distribution, SHA-256 digests, exact commit, method/profile
   changes, known limits and validation summary. Verify uploaded asset bytes.
5. Update installation/adoption guides to distinguish the published release from
   future preparation. Publication is not a Builder deployment.

## Builder adoption

Prepare a separate PR in `HHS/simpler-grants-pdf-builder` after package publication:
update the verified artifact dependency and lockfile, saved Builder HTML profile,
standalone Word-upload HTML profile and tagged/generic PDF profiles if included
in adoption scope. Preserve historical snapshots and recalculate under new
identities. Verify each conversion path before deploying to development and
then production through `HHS/simpler-grants-gov`'s Deploy NOFOs workflow.

This release-preparation task authorizes package publication after the gates;
it does not authorize a Builder dependency change or application deployment.
