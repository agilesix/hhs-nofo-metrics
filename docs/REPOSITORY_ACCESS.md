# Repository access and approvals

Ben (`@benbrasso`) and Mike (`@mikec-ai`) are the designated mergers and
release operators. Contributors can propose changes and leave reviews. PR
approval is optional: either designated merger may merge their own PR after
required CI passes and review discussions are resolved. GitHub does not allow
authors to approve their own PRs, but an approval is not required here.
Request the other's review when a change would benefit from it.

## Repository settings

Enforcement lives in [repository rulesets](https://github.com/agilesix/hhs-nofo-metrics/settings/rules),
not in this document. The rulesets configured on October 27, 2026 are:

- **Main merges - Ben and Mike:** only these two users can update `main`,
  through a PR. This exception applies only to this ruleset.
- **Main review and CI requirements:** no bypass actors; require a PR and
  resolved review threads, with zero required approvals. Code-owner and
  latest-push approvals are not required. Require up-to-date branches and
  the GitHub Actions checks `Python 3.11`,
  `Python 3.14`, `Public boundary and package smoke test`, and `Secret scan`.
  Block deletion and force pushes to `main`.
- **Release tags - Ben and Mike:** only these two users can create `v*` tags.
- **Release tags are immutable:** block updating or deleting existing `v*` tags,
  with no bypass actors. Corrections require a new version, not a moved tag.

A CODEOWNERS file is not needed for this policy. The restriction on who may
merge is enforced by the separate main-update ruleset, not by PR approvals.
Optional human review remains useful; an agent-generated review is not
independent human approval. Review policy changes do not waive the release
process's separate agreement and evidence requirements.

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

## Administrator access and follow-up

Existing administrator access was retained for `mutsuoara` and `a6-admin`, in
addition to Ben and Mike. Under the active rules, these other administrators
cannot merge to `main` or create version tags, but administrators can change
or remove repository rules and environments. They also retain manual GitHub
Release publishing permissions through their repository role. Organization
owners can retain administrative authority regardless of direct access.

For exclusive release-publishing access, an organization administrator must
review [repository access](https://github.com/agilesix/hhs-nofo-metrics/settings/access),
reduce other accounts to read/triage where appropriate, and check inherited
team/organization access and external registry/deployment credentials. Do not
remove organizational administration or emergency access without identifying
its owner and purpose. Changes to designated owners require coordinated updates
to ruleset actors, environment reviewers, and downstream permissions.

For GitHub's behavior, see [rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets),
and [deployment environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).
