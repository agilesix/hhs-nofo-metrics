# Changelog

All notable changes to this project are documented here. The project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). Profiles, methods,
adapters, and result schemas also carry their own immutable versions because a
package release may support more than one measurement contract.

## [Unreleased]

No changes yet.

## [0.5.0] - 2026-08-11

Initial release candidate.

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
- A versioned external adapter-plugin contract.
- A compact CLI for analysis and contract inspection.

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

### Known limitations

- The HHS scope policy and passive-voice method remain provisional and are not
  represented as HHS-approved or Microsoft Word-equivalent.
- Generic flat-PDF results are always estimates with low reliability.
- The package calculates and explains metrics; consumers own display bands,
  persistence, dashboards, and policy interpretation.
