# NOFO Checker integration

## Current local proof

NOFO Checker can incrementally centralize metric behavior without changing its
existing extraction, repeated-edge selection, page metrics, sentence inventory,
triage, or model-assisted review. The safe first seam is the package's exported
v1 tokenizer, sentence splitter, syllable estimator, and readability methods
operating on NOFO Checker's existing selected text.

This is deliberately not the same as replacing Checker metrics with a package
PDF profile. A later migration must deliberately choose the tagged-PDF estimate
or the lower-confidence generic-PDF fallback and calibrate the resulting scope.

The private integration proof uses a local NOFO Checker checkout on branch:

```text
branch: codex/hhs-nofo-metrics-integration
```

The original proof installed the built `hhs_nofo_metrics-0.1.0` wheel into NOFO Checker's
virtual environment. No sibling path, editable requirement, wheel, or copied
package source is committed to NOFO Checker.

## Compatibility evidence

The package v1 methods reproduced the prior Checker output on all five formula
metrics for four representative PDFs, including repeated-edge, textless-page,
modern Builder, and direct-Word-render cases. The integration adds provenance
but does not change numeric metrics or routing.

The raw parity profile intentionally differs from normal Checker output on PDFs
with repeated headers and footers because raw parity retains that content. That
difference is expected and demonstrates why method parity and profile policy
must remain separately observable.

## Distribution blocker

The integration must not be released until this package has a stable,
installable artifact available to every NOFO Checker user. Preferred:

```text
hhs-nofo-metrics==0.5.0
```

from PyPI or another public package registry. An immutable public Git commit is
a temporary second choice. Do not ship a local file URL, sibling-relative path,
editable dependency, private Git URL, mutable branch reference, submodule, or
vendored copy.

After publication, add the pinned dependency to NOFO Checker's distributed
requirements, environment diagnostics, setup documentation, clean-clone CI,
and packaged-skill installation tests before merging the integration branch.
