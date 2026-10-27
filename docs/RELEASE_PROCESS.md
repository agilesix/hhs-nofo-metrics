# Release process

This checklist separates public package verification from private evidence.
Source documents and row-level calibration data never enter this repository.

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
[installation guidance](INSTALLATION.md). See
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

Before designating a release for integration, evaluate a frozen private cohort
containing at least:

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
source follows its intended analysis path.

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
   [reuse and updates](REUSE_AND_UPDATES.md).

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
