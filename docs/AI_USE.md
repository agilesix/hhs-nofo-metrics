# AI use and contribution guidance

This page explains how this package calculates metrics and how AI assistance
fits into contributing. It applies to this repository and its built-in analysis
paths, not to every feature of NOFO Builder or another consuming application.

This guidance does not supersede applicable HHS or HHS Office of Finance policies
on AI use, data handling, cybersecurity, or Rules of Behavior. It does not
approve a tool, authorize particular data processing, or replace required
organizational approvals. Contributors remain responsible for following those
requirements alongside the repository rules below.

## How the package calculates metrics

The built-in analysis paths use deterministic, versioned extraction, selection,
tokenization, sentence and syllable rules, passive-voice heuristics, and
arithmetic. They do not ask a generative-AI model to calculate scores, rewrite
source text, decide which content counts, or classify passive sentences.
Document content is not sent to a generative-AI service as part of those
built-in calculations.

A passive classifier here is a bounded rule-based method, not a generative-AI
review of the writing. Its known misses and false positives still matter.
Deterministic behavior makes an identified implementation reproducible; it does
not establish linguistic accuracy, Word parity, HHS approval, accessibility,
clearance, or overall document quality. See [methodology](METHODOLOGY.md) and
[the architecture](ARCHITECTURE.md) for the actual calculation boundaries.

A consuming application can have separate AI features or document-conversion
services. For example, a cloud-enabled Word exporter is a separate data flow,
not evidence that this package uses generative AI. Evaluate those services and
their data permissions separately; this page makes no claims about all consumer
or contributor tools staying local.

## Appropriate contribution assistance

When permitted by applicable policies and tool approvals, AI may help with:

- drafting or explaining code and documentation;
- proposing fixes, refactors, and review questions;
- creating invented test inputs and candidate test cases; and
- investigating failures and suggesting validation steps.

Use public repository code/documentation and synthetic inputs appropriate for
the approved tool. Contributors must inspect the output, understand the change,
and verify it against the intended contract. AI-written tests are proposals:
check their expected results independently, especially sentence boundaries,
selected text, and metric numerators/denominators. A test that repeats the same
implementation mistake is not independent evidence.

## Inputs and practices to exclude

- Do not use pre-decisional NOFOs or pre-decisional information about NOFOs for
  repository work or supply them to AI tools for that work. Do not put sensitive
  excerpts, derivatives, credentials, or other restricted information into
  prompts, generated files, logs, issues, PRs, or attachments. Temporary and
  ignored files are not an exception.
- Do not assume public repository access or this guidance authorizes an external
  upload. Confirm source eligibility, applicable tool/data approvals, and the
  authorized task scope before using a service. When eligibility is unclear,
  use an invented substitute and seek guidance from the responsible user or
  organizational authority.
- Do not fabricate sources, policy authority, test runs, human reviews, release
  approvals, or validation results. Distinguish proposed checks from completed
  checks and synthetic evidence from actual producer or deployment evidence.
- Do not use generated scores or assessments to replace the selected versioned
  calculation, or silently alter formulas, scope, or historical results to fit
  an AI answer or a comparator's score.
- Do not treat an AI response or automated review as a substitute for required
  human review, organizational decisions, or explicit release/deployment
  authorization. Agents may execute actions that have actually been authorized.

The [public repository boundary](PUBLIC_REPOSITORY_BOUNDARY.md) and
[agent instructions](../AGENTS.md) apply regardless of which tool is used.
Even publicly released source corpora and their conversions remain outside Git
under that boundary. Automated scans cannot determine public-release eligibility
or certify compliance with applicable policies.

## Review and accountability

The submitting contributor remains accountable for correctness, security,
licensing, and the evidence supporting a change, whether or not AI assisted.
Follow [contribution guidance](../CONTRIBUTING.md), preserve versioned contracts,
and run checks appropriate to the change. Report checks actually performed and
limitations that remain.

If AI assistance materially influenced a contribution, briefly describe its role
and the verification performed in the PR. Do not include sensitive prompts,
transcripts, or source material as a disclosure mechanism. Model output alone is
not a citation, policy decision, or validation receipt.

## Proposing AI in an analysis path

Introducing AI into runtime analysis would require a separate explicit proposal
and review of its purpose, data flows, applicable approvals, reproducibility,
versioned contracts, evaluation, and consumer-facing limitations. It must not be
introduced as an unannounced implementation substitution under an existing
measurement identity. Follow the [release policy](RELEASE_PROCESS.md) and the
relevant program decision process; merging this guidance authorizes no new AI
service, data transfer, calculation method, or deployment.
