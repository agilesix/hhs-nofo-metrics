# Documentation guide

Start with the [project README](../README.md) for installation, profile selection,
and API/CLI examples. The installed `profiles list`, `profiles show`, and
`adapters list` commands describe the actual installed contracts. Documentation
on a development branch may include changes that have not been released.

## Using and understanding the package

| Document | Use it for |
| --- | --- |
| [Installation](../README.md#installation) | Published artifact pins, hashes, and environment reproducibility |
| [Consumer updates](INTEGRATION_CONTRACT.md#consumer-updates) | Release notifications, explicit upgrades, and preservation of historical identities |
| [Integration contract](INTEGRATION_CONTRACT.md) | Inputs, profiles, result schemas, statuses, errors, and consumer responsibilities |
| [Methodology](METHODOLOGY.md) | Measurement scopes, formulas, sentence selection, and provisional policy limits |
| [Architecture](ARCHITECTURE.md) | Runtime paths, module responsibilities, adapters, and invariants |
| [Builder guide](consumers/NOFO_BUILDER.md) | Semantic HTML integration and consumer-owned persistence |
| [Checker integration](NOFO_CHECKER_INTEGRATION.md) | Historical integration proof and distribution requirements |

## Contributing and releasing

| Document | Use it for |
| --- | --- |
| [Contributing](../CONTRIBUTING.md) | Setup, checks, versioning, tests, and evidence expectations |
| [Agent guidance](../AGENTS.md) | Repository-specific instructions for coding agents |
| [Release process](RELEASE_PROCESS.md) | Release decisions, patch/minor/major versions, dependencies, tags, publication, and gates |
| [Public repository boundary](PUBLIC_REPOSITORY_BOUNDARY.md) | What belongs in Git and what must remain private |
| [Security policy](../SECURITY.md) | Reporting sensitive findings |
| [Changelog](../CHANGELOG.md) | Released changes and the current unreleased candidate |

[Bug reports](../.github/ISSUE_TEMPLATE/bug_report.md),
[change requests](../.github/ISSUE_TEMPLATE/change_request.md), and the
[PR template](../.github/pull_request_template.md) prompt for evidence, output
impact, and release/consumer dependencies.

## Adoption and validation records

- [Passive classifier correction](PASSIVE_V4_ADOPTION.md): corrected profile
  references, remaining method limitations, and downstream adoption checks.
- [Nested table paragraph continuity](NESTED_TABLE_ADOPTION.md): candidate
  package/adapter identities, synthetic reference counts, supported structures,
  and pending Word-export and Builder validation.

An adoption note records requirements and available evidence; it does not by
itself establish that a release was published or a consumer was deployed.
Private-cohort receipts belong outside Git. Link a sanitized verification summary
when evidence becomes available, and keep pending checks explicit.
