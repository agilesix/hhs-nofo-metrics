# Installing and identifying a release

As verified on October 27, 2026, the latest published release is
[0.6.0](https://github.com/agilesix/hhs-nofo-metrics/releases/tag/v0.6.0), published
October 16, 2026, from commit
`b38496f5b90e88b0491d658a3151b04b299add53`. The local 0.6.1 candidate documented
in [nested table adoption](NESTED_TABLE_ADOPTION.md) is not a published release.
An installed package version does not establish which version another system
has deployed.

## Pinned release artifact

Use Python 3.11 or newer. The release wheel supports the package's Python API
and CLI without a web framework or Microsoft Word.

```bash
python3 -m venv .venv
curl --fail --location \
  'https://github.com/agilesix/hhs-nofo-metrics/releases/download/v0.6.0/hhs_nofo_metrics-0.6.0-py3-none-any.whl' \
  --output hhs_nofo_metrics-0.6.0-py3-none-any.whl
```

Verify the downloaded bytes before installation:

```bash
.venv/bin/python - <<'PY'
import hashlib
from pathlib import Path

artifact = Path('hhs_nofo_metrics-0.6.0-py3-none-any.whl')
expected = '7fc342f8bc0b7f78cf876ef41de847cf09404cdfe1045db10bd908df338ca81c'
actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
if actual != expected:
    raise SystemExit('Release artifact SHA-256 mismatch; installation stopped.')
print('Release artifact SHA-256 verified.')
PY
```

Install only after the check succeeds:

```bash
.venv/bin/python -m pip install ./hhs_nofo_metrics-0.6.0-py3-none-any.whl
.venv/bin/hhs-nofo-metrics --version
.venv/bin/hhs-nofo-metrics profiles list --json
.venv/bin/hhs-nofo-metrics adapters list --json
```

The version command should report `0.6.0`. The profile inventory contains six
references; tagged adapter `0.1.7`, generic adapter `0.4.0`, and HTML adapter
`0.1.1` are published in this release.

Both released assets were downloaded and their SHA-256 digests matched the
[release metadata](https://api.github.com/repos/agilesix/hhs-nofo-metrics/releases/tags/v0.6.0):

| Asset | SHA-256 |
| --- | --- |
| `hhs_nofo_metrics-0.6.0-py3-none-any.whl` | `7fc342f8bc0b7f78cf876ef41de847cf09404cdfe1045db10bd908df338ca81c` |
| `hhs_nofo_metrics-0.6.0.tar.gz` | `f6b6c3a8c36b9500d6bdf00300be2b530a7226d1db759dd6ff2ccad47181b721` |

The sdist is an alternative source artifact and requires build tooling. It has
a different digest from the wheel. For later releases, record the selected
asset URL and expected digest together during review; do not reuse these hashes.
Keep downloaded artifacts outside this repository's tracked files.

## Reproducible consumer environments

The example verifies the package artifact; it does not freeze every transitive
dependency. Production consumers should lock the full environment, including
extraction dependency versions and artifact hashes, using their existing
packaging process. For pip's `--require-hashes` mode, all requirements and
transitive dependencies must be pinned and hashed; hashing only this package
is not a complete requirements lock. See
[pip's secure-install guidance](https://pip.pypa.io/en/stable/topics/secure-installs/).

A commit-pinned Git installation remains available for reviewed source work:

```bash
python3 -m pip install 'hhs-nofo-metrics @ git+https://github.com/agilesix/hhs-nofo-metrics.git@b38496f5b90e88b0491d658a3151b04b299add53'
```

This identifies source rather than verifying the published wheel bytes. Do not
pin production consumers to a mutable branch or an unpublished release URL.
Editable installations are for development; see [contributing](../CONTRIBUTING.md).

Choose an exact profile for every analysis, retain the returned source and
measurement identities, and follow [the upgrade process](REUSE_AND_UPDATES.md)
when adopting a release. Code versions, profile choices, policy approval, and
consumer deployment are separate facts.
