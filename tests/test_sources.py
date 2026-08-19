from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path

import pytest

from hhs_nofo_metrics import InputError
from hhs_nofo_metrics.sources import (
    SourceArtifact,
    SourceBundle,
    materialize_source_bundle,
)


class UnseekableBytesStream:
    def read(self) -> bytes:
        return b"stream payload"

    def tell(self) -> int:
        raise OSError("not seekable")


class BrokenStream:
    def read(self) -> bytes:
        raise OSError("read failed")


def test_source_artifact_and_bundle_validate_public_identifiers() -> None:
    with pytest.raises(ValueError, match="artifact kind"):
        SourceArtifact(name="primary", kind=" ", source=b"")
    with pytest.raises(ValueError, match="artifact media_type"):
        SourceArtifact(name="primary", kind="pdf", source=b"", media_type="")
    with pytest.raises(ValueError, match="primary artifact name"):
        SourceBundle(primary=SourceArtifact(name="document", kind="pdf", source=b""))


def test_materialized_bundle_supports_lookup_and_unseekable_binary_stream() -> None:
    bundle = SourceBundle.from_pdf(UnseekableBytesStream())

    with materialize_source_bundle(bundle) as materialized:
        assert materialized.artifact("primary") == materialized.primary
        assert materialized.primary.path.read_bytes() == b"stream payload"
        with pytest.raises(KeyError, match="missing"):
            materialized.artifact("missing")


def test_materialization_accepts_bytearray_and_memoryview() -> None:
    for source in (bytearray(b"bytearray"), memoryview(b"memoryview")):
        with materialize_source_bundle(SourceBundle.from_pdf(source)) as materialized:
            assert materialized.primary.path.read_bytes() == bytes(source)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (StringIO("text"), "PDF stream must return bytes"),
        (BrokenStream(), "Unable to read PDF stream: read failed"),
        (object(), "must be a path, bytes, or a binary file-like object"),
    ],
)
def test_primary_stream_and_source_failures_use_input_error(
    source: object,
    message: str,
) -> None:
    bundle = SourceBundle.from_pdf(source)  # type: ignore[arg-type]

    with pytest.raises(InputError, match=message):
        with materialize_source_bundle(bundle):
            pass


def test_missing_primary_and_auxiliary_paths_have_distinct_errors(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.pdf"
    with pytest.raises(InputError, match="PDF not found"):
        with materialize_source_bundle(SourceBundle.from_pdf(missing)):
            pass

    bundle = SourceBundle(
        primary=SourceArtifact(name="primary", kind="pdf", source=b"%PDF"),
        auxiliaries=(
            SourceArtifact(
                name="manifest",
                kind="json",
                source=tmp_path / "missing.json",
            ),
        ),
    )
    with pytest.raises(InputError, match="Artifact 'manifest' not found"):
        with materialize_source_bundle(bundle):
            pass


def test_stream_position_is_restored_even_when_reading_fails() -> None:
    class PartiallyBrokenStream(BytesIO):
        def read(self, *args: object, **kwargs: object) -> bytes:
            raise ValueError("broken payload")

    stream = PartiallyBrokenStream(b"payload")
    stream.seek(3)

    with pytest.raises(InputError, match="broken payload"):
        with materialize_source_bundle(SourceBundle.from_pdf(stream)):
            pass
    assert stream.tell() == 3
