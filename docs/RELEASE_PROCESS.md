# Release process

This checklist separates public package verification from private evidence.
Source documents and row-level calibration data never enter this repository.

## When to make a release

This is the initial working policy for maintainer review. Releases are driven
by a useful, reviewed change that consumers need to install, not by every merge
or a fixed calendar. Merging a PR, publishing a package, adopting it in Builder,
and approving a measurement policy are separate decisions.

- Release a focused bug fix when consumers need the correction and its scope,
  output impact, validation, and remaining limits are understood.
- Batch compatible improvements when doing so reduces consumer upgrade effort
  without delaying a needed fix. Documentation-only changes normally reach
  readers through `main` and can join the next package release; they do not
  require a package release on their own.
- Do not wait for every open PR. Wait for an actual dependency, a change that
  must ship together for correctness/compatibility, or unresolved evidence that
  prevents an honest release claim. Older open PRs may already be superseded;
  assess their content rather than treating the open list as a release queue.
- If another PR changes the same extraction/method path or validation baseline,
  explicitly include it or defer it. Freeze the included commits before the
  final release checks. Any subsequent change to the candidate requires checking
  its impact and rerunning affected checks; the final tagged source and built
  artifacts must pass the complete package gate.

## Who decides and where the decision is recorded

The initial lightweight working convention is **Ben and Mike agree on release
scope and timing**, with Ben coordinating the consumer need and Mike reviewing
technical readiness. Agree explicitly on any change to designated maintainers
and reflect it in [repository access controls](REPOSITORY_ACCESS.md). Record the
agreement in a release-preparation PR or linked release issue, rather than
leaving the decision only in a local chat. This convention does not appoint new
organizational authorities. See [repository access](REPOSITORY_ACCESS.md) for
review, merge, tag, and release-environment controls and their limits.

Ben or Mike performs the explicitly authorized
tag/release action after the gates pass. Agents may prepare the candidate,
checks, notes, and artifacts within the requested task. A request to implement
or merge a fix alone does not authorize an agent to publish a release, select
unapproved policy, or deploy a consumer. Obtain explicit authorization for those
separate actions when it has not already been given in the conversation.

HHS Office of Grants program direction and formal decisions about measurement
policy remain separate from this technical release convention. A maintainer
release decision does not turn provisional methods into approved HHS policy.
Existing HHS and organizational public-information requirements still apply;
see [the public boundary](PUBLIC_REPOSITORY_BOUNDARY.md).

Use this compact decision record in the release-preparation PR or linked issue:

- **Release:** intended package version, included PRs/commit, purpose, and why now.
- **Dependencies:** PRs that must land first; related work deliberately deferred.
- **Compatibility:** API/CLI/schema impact, changed adapter/method/profile
  identities, expected score changes, and retained historical behavior.
- **Evidence:** package CI, focused reference checks, build/install/hash checks,
  and the required real-document gate's sanitized outcome. Record unavailable
  checks and unresolved mismatches explicitly; do not call them passes.
- **Known limits:** what remains unsupported, whether it affects the promised
  scope, and the maintainers' disposition. A reproducible error in the behavior
  claimed as repaired blocks that claim. A separately understood, pre-existing
  unsupported case is not automatically a reason to wait for every future fix;
  the maintainers must explicitly accept the bounded scope and document it.
  This disposition does not waive the required gates below.
- **Decision:** scope/timing agreement, technical reviewer, publisher, and date;
  an explicit publish/hold decision and outstanding conditions.
- **Consumer follow-up:** who prepares the downstream upgrade and its separate
  upload/report verification. Publication does not automatically update Builder.

## Choosing a version

Use [Semantic Versioning](https://semver.org/spec/v2.0.0.html) as the vocabulary
for package compatibility. Version size describes the contract impact, not the
number of files, development effort, or importance of a change.

| Change | Package version choice | Example and release note expectation |
| --- | --- | --- |
| Backward-compatible correction to intended behavior | Patch, such as `0.6.0` to `0.6.1` | Correct extraction while preserving API/result shape; identify affected adapter/resolver and expected score changes |
| Backward-compatible capability or optional measurement contract | Minor, such as `0.6.1` to `0.7.0` | Add an opt-in profile or supported capability while retaining earlier contracts; explain explicit consumer adoption |
| Incompatible public contract change after 1.0 | Major, such as `1.4.2` to `2.0.0` | Remove/change supported API behavior or require an incompatible consumer migration; document migration and schema support |
| Documentation or repository guidance only | Usually no standalone package bump | Publish guides through reviewed repository changes; include them in the next package release if applicable |

The project is currently **0.x**. SemVer treats that as initial development,
not a stable public-API promise. Our additional working convention is to use a
new **0.x minor version** for an intentionally incompatible change, with an
explicit migration note, rather than hide it in a patch. Preserve released
measurement contracts even during 0.x development. Moving to **1.0.0** is a
separate, deliberate statement that the supported public API and compatibility
policy are stable enough to commit to; it is not a declaration of HHS approval,
Word parity, or clearance compliance.

Package, profile, method, adapter/resolver, and result-schema versions serve
different purposes. Advance the identity of each output-affecting component
that changes; never rewrite a released profile/method/schema in place. A new
package does not imply every component needs the same number. Additive versus
incompatible result-shape changes need the appropriate new schema identity and
consumer handling, regardless of the package version chosen.

A **patch may change metric values** when it corrects extraction or another
implemented bug. "Compatible" does not mean identical scores under changed
code: retain complete package/adapter/method/dependency identities and describe
the expected delta. An intentional measurement-policy change is not merely a
patch correction; introduce the appropriate new profile/method and obtain the
relevant program decision without silently changing existing policy contracts.

The current release validator/tag workflow supports normal `vMAJOR.MINOR.PATCH`
versions. An unpublished candidate can be reviewed at a commit and tested with
private build artifacts. If prerelease tags such as `v0.7.0-rc.1` are wanted,
first extend and test the tooling and document the prerelease installation
contract; do not label an unvalidated normal release as a candidate after
publishing it.

## Current release preparation

The user has authorized preparation and publication of 0.7.0, including the
new opt-in definition-modifier profiles and the already-merged nested-table
repair. For this release, Ben has explicitly authorized proceeding without a
separate agreement from Mike. This records the release-specific instruction;
it does not change the general maintainer convention above. Ben subsequently
explicitly authorized deferring the five-source real-document gate for this
release, relying on the sanitized PR #25 investigation and synthetic/public-path
checks. The gate is recorded as not run, not passed; the general gate remains
unchanged for future releases. Public-information, automated CI and program
requirements are not waived. See the
[0.7.0 preparation record](RELEASE_0_7_0.md) for the frozen scope and remaining gates.

## Applying this to candidate 0.6.1

PR #14 proposes a bounded extraction correction with unchanged formulas,
released profiles, and result schemas, so **0.6.1 is the proposed patch version**.
It is not a promise that all Word/PDF paragraph continuity is repaired. The
[Word-export observation](NESTED_TABLE_ADOPTION.md#word-export-observation)
records a distinct exporter-created object case where the candidate and 0.6.0
both miss the source paragraph denominator; that is not passing evidence for
Word continuity. Before publication, Ben/Mike or their designated maintainers
must settle the bounded release claim, assess any actual PR dependencies, and
complete the required gates. If the intended release must repair that Word
case too, hold or expand the scope and validate it first. Do not change formulas
or join unrelated objects merely to make the example pass.

## What the tags mean

The repository's [Tags page](https://github.com/agilesix/hhs-nofo-metrics/tags)
lists Git references such as `v0.6.0`. Each names a source commit for a package
version; `v0.6.0` corresponds to package version `0.6.0`. That commit includes
both code and documentation, so a tag can also identify the guides associated
with that release. A moving branch such as `main` can contain later work.

A [GitHub Release](https://github.com/agilesix/hhs-nofo-metrics/releases) is the
published record attached to a tag: release notes and uploaded wheel/sdist
assets. A tag alone does not mean an installable wheel was uploaded, a private
cohort passed, or a consumer upgraded. GitHub's automatically generated source
ZIP/tar archives are snapshots of the repository; they are distinct from the
built wheel and Python source distribution whose hashes appear in
[installation guidance](GETTING_STARTED.md#installation). See
[GitHub's release explanation](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

These version tags are separate from issue/PR labels such as `documentation`,
profile/method versions such as `html@0.5.0`, and semantic HTML/PDF tags such as
P or H2. A package release can contain several independently versioned profiles
and methods. The package tag does not need to match those component versions.

Use `vMAJOR.MINOR.PATCH` for stable package release tags. Existing history
contains both annotated and lightweight tags; neither type by itself proves
release approval or prevents later modification. For new releases, prefer an
annotated tag with a release message. Preserve published tags and asset bytes:
correct a published problem with a new version rather than moving its tag or
replacing a wheel under the old identity. Record commit and artifact digests in
addition to the human-readable tag. Tag-protection or immutable-release settings
are separate repository administration controls; this change does not configure
them or assert that they are already enabled.

## Package gate

Run `python tools/check_release_identity.py` during development. It checks that
`pyproject.toml` and the source fallback version agree. For a stable release,
`python tools/check_release_identity.py --tag vMAJOR.MINOR.PATCH` also checks
the tag against that version and requires one valid dated changelog heading.
Use the actual version rather than the placeholder.

1. Confirm the changelog and package version describe the same release.
2. Run formatting, lint, tests, coverage, and pre-commit checks.
3. Run `tools/check_public_repo.py --history`.
4. Build the wheel and source distribution.
5. Run both distribution-boundary checks and install each artifact in a clean
   environment.
6. Confirm the CLI default is TOON 4.1, `--json` is valid JSON, and the Python
   API exports `AnalysisResult`.

## Private real-document gate

Before designating a release for integration, evaluate a frozen cohort in a
separately approved validation environment, using sources confirmed eligible
under [the public boundary](PUBLIC_REPOSITORY_BOUNDARY.md). "Private" describes
the evaluation workspace and detailed receipts; it is not permission to use
pre-decisional information. The cohort contains at least:

- one semantic Builder HTML export;
- one native Builder/Prince tagged PDF;
- one Builder Word-to-PDF export;
- one non-Builder tagged PDF; and
- one untagged or structurally degraded PDF.

Store the receipt outside Git. The receipt should contain only the package
commit, profile references, a cohort-manifest hash, document counts, result and
reliability distributions, unexpected-error counts, and the reviewer/date. It
must not contain filenames, paths, extracted text, source metadata, or
document-level records.

The gate passes when every input returns either a schema-valid result or a
documented typed error, no source text or local path crosses the result
boundary, tagged blank pages do not count as extraction failures, and each
source follows its intended analysis path. In addition to those technical
checks, output-changing fixes need focused comparison against independently
checked source text, boundaries, and metric numerators/denominators on the
claimed supported path. A schema-valid numeric result alone does not establish
correct extraction. Record and assess discrepancies using the release decision
record above; do not present a known mismatch as a validation pass.

## Public-release gate

Before making the repository or a distribution public, confirm that the MIT
copyright attribution in `LICENSE` remains correct for the intended release.
Do not infer ownership from dependencies or organizational affiliation. Re-run
the history and secret scans after the final commit and publish from a clean
export if any private material ever entered Git history.

## Tagging, checks, and publication

After the package, private real-document, and public-release gates pass:

1. Finalize the package version, source fallback, CI smoke expectations, and
   changelog. Move the released changes out of `Unreleased` into a heading such
   as `## [0.6.1] - YYYY-MM-DD`, using the actual release date. Keep future work
   under `Unreleased`. Candidate 0.6.1 is not ready to tag merely because it
   builds locally.
2. Review and commit the final release source. Run the identity check with the
   intended tag before pushing it. Record the exact reviewed commit.
3. Create an annotated `vMAJOR.MINOR.PATCH` tag on that commit and push that
   single tag. Do not move an existing published tag. Tag creation/push remains
   an explicit maintainer release action.
4. Wait for **CI on the tag's commit**. The workflow runs Python tests,
   package/sdist builds and clean-install checks, public/history boundary checks,
   and the secret scan. Its release-identity step rejects a mismatched package
   tag, fallback version, or missing/invalid dated changelog entry. A failed run
   records a failure; it does not prevent the Git tag from existing.
5. After tag CI passes and all manual gates are satisfied, publish a GitHub
   Release for that tag with the reviewed wheel/sdist assets, their SHA-256
   digests, commit, changes, validation, and remaining limitations. Check the
   uploaded asset bytes against the recorded hashes. Release publication and
   asset upload are explicit maintainer actions, separate from pushing a tag.
6. Update the release/install and adoption documentation to distinguish the
   published version from future candidates, then notify consumers through the
   release record. Consumers upgrade explicitly; see
   [consumer updates](INTEGRATION_CONTRACT.md#consumer-updates).

The [CI workflow](../.github/workflows/ci.yml) runs on PRs, pushes to `main`,
manual dispatch, and pushes of `v*` tags containing this workflow. Older tagged
commits do not acquire a newer workflow retroactively. A published GitHub
Release is not configured as an additional CI trigger; check the tag run.
GitHub documents [branch/tag trigger filters](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

This automation validates release inputs and the tagged build. It does not
create/move tags, upload/publish artifacts, sign releases, approve methodology,
run the private cohort, deploy consumers, or rewrite historical results. No
scheduled task is needed: tag pushes are the relevant event. Read-only CI
permissions are retained. Local checks can verify the validator and workflow
configuration; the hosted tag run is confirmed only after the changes and an
intentional release tag are pushed.
