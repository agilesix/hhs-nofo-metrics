# Reusing whole-NOFO calculations and adopting updates

The reusable implementation is the public
[hhs-nofo-metrics package](https://github.com/agilesix/hhs-nofo-metrics).
Start with [verified installation](INSTALLATION.md), the
[README API/CLI examples](../README.md), [methodology](METHODOLOGY.md), and the
[consumer contract](INTEGRATION_CONTRACT.md). Existing executable code and guides
are the accepted starting point in
[Builder discovery #1234](https://github.com/HHS/simpler-grants-pdf-builder/issues/1234);
[this documentation follow-up](https://github.com/agilesix/hhs-nofo-metrics/issues/13)
does not build another engine or service.

## Direction, maintenance, and approval

| Responsibility | Role |
| --- | --- |
| Program direction and decisions about the measurement approach | HHS Office of Grants owns and directs this work in the program sense |
| Implementation and code maintenance on its behalf | Agile Six, acting as a contractor |
| Hosting | The public repository is hosted under Agile Six; its location does not define program authority |
| Legal/IP ownership and licensing | Not determined by the program-role statement; the existing [MIT license and attribution](../LICENSE) remain unchanged |
| Formal method approval | Must be established separately; bundled profiles and classifiers remain provisional |
| Consumer integration and operation | Each consuming system owns its UI, storage, permissions, thresholds, orchestration, and deployment |

These distinctions follow the accepted
[roles clarification](https://github.com/HHS/simpler-grants-pdf-builder/issues/1234#issuecomment-6450690634).
Publishing maintained code is not a declaration that every heuristic has formal
HHS approval or that a numeric result establishes clearance.

## Reuse options and boundaries

1. **Use the Python API** when the consumer can run Python. Supply the complete
   intended NOFO source and exact profile, then retain `AnalysisResult.to_dict()`.
   Prefer semantic HTML when the source system owns ordered content; select
   tagged or generic PDF explicitly for PDF-only workflows.
2. **Use the existing CLI** across a process boundary when that is a better fit.
   `--json` makes terminal receipts/errors JSON. The complete versioned analysis
   result is written to `--output`; standard output is not the full result.
   Check exit status (`0` success, `2` usage, `1` expected runtime failure) and
   metric statuses in the result file.
3. **Use the documentation** to understand scope, method choices, uncertainty,
   and provenance even when execution is shared. Separately reimplementing
   formulas can drift if extraction, tokens, or sentence inventories differ.
4. A **consumer-hosted wrapper** around this same package can be considered
   later if a stack requires it. No wrapper, hosting service, or selected
   GrantSolutions architecture is included here.

The package accepts PDF and explicit UTF-8 HTML source bundles. It does not
accept DOCX directly. Word conversion is currently a **NOFO Builder adapter**:
Builder converts Word body content to HTML and invokes the package HTML profile.
That conversion can omit headers, footers, text boxes, images, and unsupported
content, and can retain writer instructions converted as ordinary text. A Word
upload result is not evidence that a DOCX parser ships in this package or that
the package measured every part of the Word file.

Builder's [integration guide](consumers/NOFO_BUILDER.md) and pinned
[worker source](https://github.com/HHS/simpler-grants-pdf-builder/blob/c3fad94/nofos/nofos/pdf_readability_worker.py)
describe this boundary. At that reviewed source revision, HTML profile `0.5.0`,
tagged PDF `0.6.0`, and generic PDF `0.5.0` are selected. Source configuration is
not proof of the version deployed in a given environment.

The scope is one aggregate result for the supplied whole NOFO, subject to the
selected content policy. Announcement Module's additional section/subsection/
paragraph functionality is acknowledged and excluded. GrantSolutions outreach,
its technical constraints and integration choice, a handoff, service construction,
and cross-system parity tests are subsequent work. Passive-sentence accuracy
remains the separate [Builder #1231](https://github.com/HHS/simpler-grants-pdf-builder/issues/1231).

## How consumers learn about changes

Use [GitHub Releases](https://github.com/agilesix/hhs-nofo-metrics/releases) and
[the changelog](../CHANGELOG.md) as the published update record. A consumer owner
can choose **Watch → Custom → Releases** on the repository and configure their
notification delivery; see
[GitHub's notification guidance](https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications).
The **Unreleased** changelog section describes prospective work, not an
available upgrade. No subscription is created by installing the package.

Release notes should identify the artifact and checksum, package commit,
output-affecting adapter/method/profile/schema changes, known limits, validation,
and adoption steps. A notification announces availability; it does not update
an installed dependency or certify a consumer deployment.

## Explicit upgrade workflow

1. Compare the published changelog/adoption notes with the consumer's currently
   pinned package, artifact digest, profile, adapter, schema support, and
   extraction dependencies. An adapter correction can change scores even if
   the profile reference is unchanged.
2. Review output impact and validation needs. Retain an earlier profile when
   continuity is intended; explicitly select a corrected profile to adopt its
   method change. Shared code does not require identical consumer targets.
3. Pin the reviewed release artifact and digest, regenerate the consumer's
   dependency lock, and test its actual source path. Validate the result schema,
   statuses, counts/denominators, warnings, and reliability before deployment.
4. For the same source revision, compare old/new contracts and explain expected
   differences. Matching formulas alone is insufficient evidence of parity.
   Use authorized real sources and store private receipts outside this repository.
5. Deploy through the consumer's ordinary process and record the installed
   package/profile/adapter identities from actual results. Installation and
   configuration checks are distinct from an authenticated end-to-end report.

Each system upgrades explicitly. Importing the same library name in two systems
does not synchronize their versions, source selection, or saved results.

## Preserve historical meaning

Retain the complete original result with source hash/revision, package identity,
profile reference/hash, method identities, adapter/configuration/dependency
identities, and schema version. Consumers must reject unknown schema versions
rather than guess their interpretation.

Treat recalculation after an upgrade as a **new analysis**, linked to the prior
source/result when appropriate. Do not overwrite old results, relabel them with
a new version, or silently reuse an old snapshot as a current calculation.
Keep old results inspectable under their original contract and compare scores
only with their source and identity differences visible. Consumers own cache
invalidation, retention, display, and permission decisions.

For example, package 0.6.0 offers both passive methods through explicit profile
pairs. The unpublished 0.6.1 adapter repair can instead change sentence scope
under an existing tagged-PDF profile. These are different upgrade decisions;
see [passive adoption](PASSIVE_V4_ADOPTION.md) and
[nested table adoption](NESTED_TABLE_ADOPTION.md).
