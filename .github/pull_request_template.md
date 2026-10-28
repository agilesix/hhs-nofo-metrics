## Change

Describe the concrete problem and resulting behavior. Link the issue; use a
closing reference only when the PR satisfies all of its acceptance criteria.

## Contract and output impact

Identify changed package, adapter/resolver, method, profile, or schema versions.
Explain whether metrics, selected content, denominators, or result shapes can
change and how earlier results remain reproducible. For documentation/tooling
changes, state that metric behavior is unchanged.

## Validation

List checks actually run and their results. For extraction or scoring changes,
include the independent reference and focused regression evidence. Distinguish
synthetic coverage from actual producer exports and private-cohort validation;
record checks that were unavailable or not applicable.

## Release and consumer follow-up

Identify required release and adoption/verification dependencies, or state
"none." A built artifact is not a published release or a verified integration.

## Review checklist

- [ ] For changes to content selection, sentence rules, formulas, input handling, or reliability (including `methods/`, `adapters/`, `profiles/`, `metric_scopes.py`, `resolved_scope.py`, or `semantic_html_engine.py` under `src/hhs_nofo_metrics/`), I re-checked and updated the [methodology summary](../docs/METHODOLOGY.md#in-brief) and [README summary](../README.md#how-the-metrics-are-calculated) as needed, or explained why neither changes. I also re-checked the HHS/Builder section if guidance or consumer behavior changed.
- [ ] Appropriate checks pass, with limitations recorded above.
- [ ] User-visible behavior and version changes appear in the changelog and relevant docs.
- [ ] Released contracts are preserved, or versioning is explained above.
- [ ] The public-boundary check passes; private evidence and generated artifacts are excluded.
- [ ] I confirmed submitted material contains no pre-decisional NOFOs or information about them and is eligible for public release under applicable HHS requirements. Automated checks do not replace this responsibility.
