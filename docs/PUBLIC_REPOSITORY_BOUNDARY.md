# Public repository boundary

This repository contains the supported metric package, its public contracts,
focused regression tests, and release tooling. It does not contain the private
or bulky research artifacts used to calibrate a particular method.

## Commit

- versioned production methods;
- command-line and Python APIs;
- schemas, profiles, and output contracts;
- focused synthetic fixtures and automated regression tests;
- methodology documentation;
- release and repository-safety checks.

## Keep outside Git

- source PDF corpora, even when the documents are publicly downloadable;
- PDF-to-Word conversions and normalized DOCX fixtures derived from a corpus;
- rendered pages, screenshots, crops, and visual-review evidence;
- full per-document reports and debug inventories;
- Airtable exports, coaching or design cohort labels, and internal bypass data;
- reviewer comments, clearance drafts, and unpublished documents;
- local absolute paths, machine configuration, and application workspaces;
- generated package artifacts and temporary files.

The default private workspace currently lives outside this repository. Its
location is deliberately not recorded in tracked files.

Private calibration work may inform a product regression test or methodology
change, but its source documents, generated packets, screenshots, local tools,
and historical notes remain outside this release repository. Git history
preserves removed experiments when maintainers need to recover them.

## Release checks

Before any public push:

1. Run `python tools/check_public_repo.py` and then
   `python tools/check_public_repo.py --history`.
2. Run the complete test suite and build the wheel from a clean checkout.
3. Inspect the wheel contents; generated corpora and local paths must be absent.
4. Review Git history, not only the current tree. If private paths or artifacts
   ever entered history, publish from a clean squashed export or deliberately
   rewrite history before making the repository public.
5. Confirm the MIT attribution, contribution guidance, and security-reporting
   process remain correct. Decide separately whether the project needs a code
   of conduct; that policy is not implied by this technical boundary.

## Decision rule

If removing the private corpus makes code unusable, parameterize and commit the
code. If removing the corpus only prevents reproduction of one historical run,
keep the run artifacts private and publish a sanitized summary.
