"""Source-bundle inputs and private materialization helpers."""

from __future__ import annotations

import hashlib
import re
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO, Iterator, TypeAlias

from hhs_nofo_metrics.errors import InputError

BinarySource: TypeAlias = (
    str | PathLike[str] | bytes | bytearray | memoryview | BinaryIO
)
PdfSource: TypeAlias = BinarySource
HtmlSource: TypeAlias = BinarySource

_ARTIFACT_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _required_string(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class SourceArtifact:
    """One caller-supplied artifact in a source bundle."""

    name: str
    kind: str
    source: BinarySource
    media_type: str | None = None

    def __post_init__(self) -> None:
        if not _ARTIFACT_NAME_RE.fullmatch(self.name):
            raise ValueError(
                "artifact name must start with a lowercase letter and contain only "
                "lowercase letters, digits, and underscores"
            )
        _required_string(self.kind, "artifact kind")
        if self.media_type is not None:
            _required_string(self.media_type, "artifact media_type")


@dataclass(frozen=True, slots=True)
class SourceBundle:
    """A primary source artifact and optional named auxiliary artifacts."""

    primary: SourceArtifact
    auxiliaries: tuple[SourceArtifact, ...] = ()

    def __post_init__(self) -> None:
        if self.primary.name != "primary":
            raise ValueError("the primary artifact name must be 'primary'")
        names = [self.primary.name, *(artifact.name for artifact in self.auxiliaries)]
        if len(names) != len(set(names)):
            raise ValueError("artifact names must be unique within a source bundle")

    @classmethod
    def from_pdf(cls, source: PdfSource) -> SourceBundle:
        return cls(
            primary=SourceArtifact(
                name="primary",
                kind="pdf",
                source=source,
                media_type="application/pdf",
            )
        )

    @classmethod
    def from_html(cls, source: HtmlSource) -> SourceBundle:
        return cls(
            primary=SourceArtifact(
                name="primary",
                kind="html",
                source=source,
                media_type="text/html",
            )
        )

    @property
    def artifacts(self) -> tuple[SourceArtifact, ...]:
        return (self.primary, *self.auxiliaries)


@dataclass(frozen=True, slots=True)
class MaterializedArtifact:
    """A validated local artifact available only during adapter execution."""

    name: str
    kind: str
    path: Path
    media_type: str | None
    sha256: str
    byte_length: int


@dataclass(frozen=True, slots=True)
class MaterializedSourceBundle:
    primary: MaterializedArtifact
    auxiliaries: tuple[MaterializedArtifact, ...] = ()

    @property
    def artifacts(self) -> tuple[MaterializedArtifact, ...]:
        return (self.primary, *self.auxiliaries)

    def artifact(self, name: str) -> MaterializedArtifact:
        for artifact in self.artifacts:
            if artifact.name == name:
                return artifact
        raise KeyError(name)


def _read_stream(
    source: BinaryIO,
    *,
    artifact_name: str,
    artifact_kind: str,
) -> bytes:
    original_position: int | None = None
    try:
        original_position = source.tell()
    except (AttributeError, OSError, TypeError, ValueError):
        pass

    if original_position is not None:
        try:
            source.seek(0)
        except (AttributeError, OSError, TypeError, ValueError):
            original_position = None

    try:
        payload = source.read()
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        if artifact_name == "primary":
            raise InputError(
                f"Unable to read {artifact_kind.upper()} stream: {exc}"
            ) from exc
        raise InputError(f"Unable to read artifact '{artifact_name}': {exc}") from exc
    finally:
        if original_position is not None:
            try:
                source.seek(original_position)
            except (AttributeError, OSError, TypeError, ValueError):
                pass

    if not isinstance(payload, bytes):
        if artifact_name == "primary":
            raise InputError(f"{artifact_kind.upper()} stream must return bytes")
        raise InputError(f"Artifact '{artifact_name}' stream must return bytes")
    return payload


def _materialize_artifact(
    artifact: SourceArtifact,
    *,
    directory: Path,
) -> MaterializedArtifact:
    source = artifact.source
    if isinstance(source, (str, PathLike)):
        source_path = Path(source).expanduser().resolve()
        if not source_path.is_file():
            if artifact.name == "primary":
                raise InputError(f"{artifact.kind.upper()} not found: {source_path}")
            raise InputError(f"Artifact '{artifact.name}' not found: {source_path}")
        suffix = f".{artifact.kind.casefold()}" if artifact.kind else source_path.suffix
        path = directory / f"{artifact.name}{suffix}"
        try:
            shutil.copyfile(source_path, path)
        except OSError as exc:
            raise InputError(
                f"Unable to stage artifact '{artifact.name}': {exc}"
            ) from exc
    else:
        if isinstance(source, bytes):
            payload = source
        elif isinstance(source, (bytearray, memoryview)):
            payload = bytes(source)
        elif hasattr(source, "read"):
            payload = _read_stream(
                source,
                artifact_name=artifact.name,
                artifact_kind=artifact.kind,
            )
        else:
            raise InputError(
                f"Artifact '{artifact.name}' must be a path, bytes, or a binary "
                "file-like object"
            )
        suffix = f".{artifact.kind.casefold()}" if artifact.kind else ""
        path = directory / f"{artifact.name}{suffix}"
        try:
            path.write_bytes(payload)
        except OSError as exc:
            raise InputError(
                f"Unable to stage artifact '{artifact.name}': {exc}"
            ) from exc

    return MaterializedArtifact(
        name=artifact.name,
        kind=artifact.kind,
        path=path,
        media_type=artifact.media_type,
        sha256=_sha256_path(path),
        byte_length=path.stat().st_size,
    )


@contextmanager
def materialize_source_bundle(
    bundle: SourceBundle,
) -> Iterator[MaterializedSourceBundle]:
    """Materialize all artifacts without exposing local paths in public results."""

    with TemporaryDirectory(prefix="hhs-nofo-metrics-") as temporary_directory:
        directory = Path(temporary_directory)
        materialized = tuple(
            _materialize_artifact(artifact, directory=directory)
            for artifact in bundle.artifacts
        )
        yield MaterializedSourceBundle(
            primary=materialized[0], auxiliaries=materialized[1:]
        )
