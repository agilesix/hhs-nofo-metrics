---
name: Bug report
about: Report an extraction, metric, API, CLI, or packaging problem
title: ''
---

## Problem

Describe what happened, the expected behavior, and who or what is affected.

## Version and input

- Package version or immutable commit:
- Profile reference:
- Adapter/resolver reference, if relevant:
- Python version and operating system:
- Source kind and producer, if known (semantic HTML, tagged PDF, generic PDF):

## Reproduction

Provide a minimal command or API call and a synthetic input or fixture generator.
Do not include pre-decisional NOFOs or information about them, including
excerpts or sensitive derivatives. You are responsible for confirming that
anything supplied is eligible for public release under applicable HHS and HHS
Office of Finance requirements; use synthetic examples when uncertain.

State whether this was reproduced against the current package, and identify
historical evidence separately. Keep private source documents, local absolute
paths, credentials, and source-bearing reports out of public issues. Follow
[SECURITY.md](../../SECURITY.md) for security reports.

## Expected and observed results

For extraction or scoring problems, compare the recovered text, reading order,
block boundaries, selected sentences, and metric numerators/denominators against
an independently checked reference. Include only synthetic text or sanitized
counts. A completed PDF analysis alone does not establish correct scores.

## Acceptance criteria

- [ ] Current behavior is reproduced, or the investigation explains why it is resolved.
- [ ] Expected behavior and regression coverage are defined.
- [ ] Output/contract changes and versioning needs are identified.
- [ ] Missing real-document evidence and release/consumer dependencies are recorded.

## Related work

Link related issues, PRs, release identities, and consumer dependencies.
