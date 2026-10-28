# HHS NOFO Metrics

HHS NOFO Metrics calculates versioned, reproducible readability metrics
for an HHS Notice of Funding Opportunity (NOFO). It gives authors and consuming
systems readability metrics and provenance for a whole NOFO under an explicit
measurement profile.

## What it measures

- Word count
- Average words per sentence
- Characters per word
- Flesch Reading Ease
- Flesch-Kincaid Grade Level
- Passive-sentence percentage

Results also include sentence-bearing block counts and average sentences per
paragraph for consumer display. The
[methodology](docs/METHODOLOGY.md) explains how the readability metrics work, which
content is counted, and the limitations of each input path.

A numeric result does not establish clearance, compliance, accessibility, or
document quality. The package does not perform generative-AI review, and its
measurement profiles and methods remain provisional. See
[AI use and contribution guidance](docs/AI_USE.md) for the package boundary and
contributor responsibilities.

## How the metrics are calculated

The readability metrics focus on content intended for applicants. Navigation,
covers, tables of contents, headers, footers, decorative material, and
instructions intended only for NOFO writers are excluded when the file's
structure identifies them.

How a Word or PDF file identifies headings, paragraphs, lists, and tables
affects what gets counted. For example, a heading identified as a heading
counts toward Word Count but is left out of the other readability metrics. A
PDF without structural tags can make reading order harder to identify on pages
with multiple columns, in tables, or around sidebars and text boxes.

The [definition modifier rule](docs/PASSIVE_V5_CANDIDATE.md) in the prepared
0.7.0 release stops counting “as defined by” alone as passive. Other passive
clauses still count. New opt-in profiles select it; historical profiles retain
their released rules. Package publication and consumer upgrades remain separate
steps; see the [release preparation record](docs/RELEASE_0_7_0.md).

Read the [plain-language explanation](docs/METHODOLOGY.md#in-brief) and
[HHS Departmental review and NOFO Builder](docs/METHODOLOGY.md#hhs-departmental-review-and-nofo-builder)
for more about what is counted, why results can differ from Microsoft Word, and
how readability metrics can support preparation of a NOFO submission package
for Departmental review.

## How it can be used

The package supports semantic HTML, tagged PDFs, and a lower-confidence fallback
for untagged PDFs. Prefer semantic HTML when a system owns ordered source
content. PDF results include reliability information to help consumers interpret
extraction uncertainty.

Systems can reuse the Python package or its command-line interface. Consumers
own their interface, storage, permissions, targets, and workflow. Word conversion
is currently handled by NOFO Builder outside this package.

## Get started

Use the [getting-started guide](docs/GETTING_STARTED.md) for installation,
profile selection, and Python API or command-line examples. Existing consumers
should review [how updates are adopted](docs/INTEGRATION_CONTRACT.md#consumer-updates).
Installing a package does not automatically update another system or select a
new measurement profile.

## Documentation

The [documentation index](docs/README.md) maps all guides. Useful starting points:

| Guide | Purpose |
| --- | --- |
| [Methodology](docs/METHODOLOGY.md) | Measurements, content selection, rationale, and limitations |
| [Getting started](docs/GETTING_STARTED.md) | Installation and engineering examples |
| [Integration contract](docs/INTEGRATION_CONTRACT.md) | Inputs, results, statuses, and consumer responsibilities |
| [Builder guide](docs/consumers/NOFO_BUILDER.md) | Using the package in NOFO Builder |
| [AI use and contribution guidance](docs/AI_USE.md) | Deterministic calculations, AI-assisted contributions, and applicable policy responsibilities |
| [Contributing](CONTRIBUTING.md) | Development setup, checks, and issue/PR guidance |
| [Release process](docs/RELEASE_PROCESS.md) | Release decisions, version tags, publication, and adoption |

See the [changelog](CHANGELOG.md) for changes and [AGENTS.md](AGENTS.md) for
repository instructions for coding agents.

## Program direction and maintenance

HHS Office of Grants owns and directs this work and decisions about the
measurement approach. Agile Six implements and maintains the code on its behalf
as a contractor. Repository hosting does not establish legal/IP ownership or
formal approval of a measurement method. The provisional implementation is not
an official HHS policy interpretation, certification, or endorsement.

## Public information only

Do not use or save pre-decisional NOFOs or information about them in this public
repository, including temporary files, commits, issues, and PRs. Users are
responsible for public-release eligibility and applicable HHS Rules of Behavior,
data-sensitivity, information-handling, and cybersecurity requirements. Use synthetic examples; see the
[public repository boundary](docs/PUBLIC_REPOSITORY_BOUNDARY.md) and
[security reporting guidance](SECURITY.md).

## License

This project is available under the [MIT License](LICENSE).
