# Changelog

All notable changes to this project are documented here. The project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). Profiles, methods,
adapters, and result schemas also carry their own immutable versions because a
package release may support more than one measurement contract.

## [Unreleased]

No unreleased changes.

## [0.5.3] - 2026-09-17

### Fixed

- Preserve navigation, header and footer exclusion roles for nested HTML headings,
  lists and table cells. Genuine body instructions remain included.
- Recognize tagged-PDF running navigation only when matching text and geometry
  are explicitly marked as artifacts on at least two other pages. This bounded
  fallback does not resolve local section contents or all navigation formats.

### Measurement identity

- HTML and tagged-PDF adapters are now 0.1.1; tagged structure resolver is 0.3.1.
  Profile policy, formulas and targets are unchanged. Results retain package and
  adapter identities so extraction changes are distinguishable.
- Consumers explicitly selecting adapter @0.1.0 must select @0.1.1 (or a current
  alias); retain package 0.5.2 to reproduce the previous extraction behavior.
- Builder's administrative-metadata correction is a separate producer change,
  not implemented by stripping metadata-like text from arbitrary documents.

## [0.5.2] - 2026-08-19

### Changed

- Moved the canonical repository and package metadata to the Agile Six GitHub
  organization. Measurement behavior and versioned profiles are unchanged.

## [0.5.1] - 2026-08-17

### Added

- Sentence-bearing semantic-block counts and average sentences per paragraph
  as source-neutral components of every sentence-scope metric result.

## [0.5.0] - 2026-08-11

Initial public release.

### Added

- A single public `analyze()` API for semantic HTML, tagged PDFs, and generic
  PDF estimates.
- Six deterministic metrics: Word Count, average words per sentence,
  characters per word, Flesch Reading Ease, Flesch-Kincaid Grade Level, and
  passive-sentence percentage.
- Versioned profiles, adapters, methods, result schemas, provenance, metric
  statuses, coverage, and warnings.
- Metric-specific reliability and include/exclude sensitivity for PDF
  estimates.
- Three versioned built-in extraction adapters with one validated internal
  contract.
- A compact CLI for analysis and contract inspection.
- MIT licensing with Agile Six Applications, Inc. attribution.
- Public package metadata, repository links, and explicit maintainer and
  non-endorsement language.
- Focused public-contract coverage for the CLI, source materialization,
  tagged-PDF structure and geometry handling, and TOON output, with an 84%
  enforced coverage floor.

### Changed

- Unified HTML and PDF calculations behind one resolved-scope metric kernel.
- Made profile selection explicit; the package no longer implies a universal
  measurement policy.
- Made semantic Builder export HTML the recommended draft-metrics source.
- Replaced the fail-closed tagged-PDF profile with a reliability-aware PDF
  estimate profile.
- Reduced the supported runtime to three intentional profiles: semantic HTML,
  tagged-PDF estimate, and generic-PDF estimate.

### Removed

- Experimental Word-parity, calibration, corpus, producer-specific, and
  historical architecture code from the release repository.
- The strict tagged-PDF profile and legacy no-profile API behavior.
- Automatic third-party adapter discovery and two unused experimental
  classification modules.

### Fixed

- Rejected unpaired Unicode surrogates at the TOON output boundary instead of
  allowing a terminal encoding failure outside the structured CLI envelope.

### Known limitations

- The HHS scope policy and passive-voice method remain provisional and are not
  represented as HHS-approved or Microsoft Word-equivalent.
- Generic flat-PDF results are always estimates with low reliability.
- The package calculates and explains metrics; consumers own display bands,
  persistence, dashboards, and policy interpretation.
