# Repository access and approvals

## Who can merge

Merge permission follows GitHub repository access: people with Write, Maintain,
or Admin access can merge PRs. Read and Triage access do not grant merging
permission. A public visitor can propose a PR or leave feedback but cannot
merge without the necessary repository access.

PR approval is optional. A person with merge permission may merge their own PR
after required CI passes and review discussions are resolved. GitHub does not
allow authors to approve their own PRs, but no approval is required here.
Request independent review when a change would benefit from it. An
agent-generated review is not independent human approval.

## Repository settings

Enforcement lives in [repository rulesets](https://github.com/agilesix/hhs-nofo-metrics/settings/rules)
and [repository access](https://github.com/agilesix/hhs-nofo-metrics/settings/access),
not in this document. The rulesets configured on October 27, 2026 are:

- **Main review and CI requirements:** no bypass actors; require a PR and
  resolved review threads, with zero required approvals. Code-owner and
  latest-push approvals are not required. Require up-to-date branches and
  the GitHub Actions checks `Python 3.11`, `Python 3.14`,
  `Public boundary and package smoke test`, and `Secret scan`.
  Block deletion and force pushes to `main`.
- **Release tags - Ben and Mike:** only `@benbrasso` and `@mikec-ai` can create
  `v*` tags.
- **Release tags are immutable:** block updating or deleting existing `v*` tags,
  with no bypass actors. Corrections require a new version, not a moved tag.

There is no separate main-update restriction or required CODEOWNERS file.
Eligible users use the normal merge button without a bypass checkbox once
requirements pass. Review policy changes do not waive the release process's
separate agreement and evidence requirements.

## Release approval and deployment limits

The [release environment](https://github.com/agilesix/hhs-nofo-metrics/settings/environments)
is restricted to `v*` tags, requires approval by Ben or Mike, prevents the job
initiator from approving their own deployment, and disables administrator
bypass. A release initiated by one therefore requires the other's approval.
Future publication workflows must explicitly use `environment: release` on
any publishing job and keep publication credentials in that environment or
use equivalently scoped trusted publishing. A different or omitted environment
does not inherit these protections. Allow only Ben or Mike to initiate future
publication workflows, including reruns; required reviewers alone control
approval, not who starts a run.

There is currently no publication or deployment workflow. Existing CI only
validates builds. Creating this environment does not publish a package or
protect manual GitHub Release creation/editing, direct registry credentials,
or deployments in consumer repositories. Those require their own access
controls. Follow [the release process](RELEASE_PROCESS.md) and obtain explicit
release/deployment authorization before acting.

## Administrator access

Administrator access is retained for `benbrasso`, `mikec-ai`, `mutsuoara`, and
`a6-admin`. All four can merge PRs after the main-branch requirements pass,
change repository settings, and manually publish GitHub Releases. The
maintainers have accepted retaining this access. The tag-creation and release
environment restrictions above remain separate from merge permission.
Organization owners can retain administrative authority regardless of direct
access.

Review direct and inherited team/organization access when granting or changing
permissions. Read or Triage is appropriate for contributors who should not
merge; Write, Maintain, and Admin grant merge access. Changes to designated
release operators require coordinated updates to tag-rule actors, environment
reviewers, and any external registry or downstream deployment permissions.

For GitHub's behavior, see [rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets) and [deployment environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).
