from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter

from hhs_nofo_metrics import (
    AdapterContractError,
    AdapterExecutionError,
    AdapterNotFoundError,
    SourceArtifact,
    SourceBundle,
    analyze,
    inspect_adapter_support,
    list_adapters,
)
from hhs_nofo_metrics import api as api_module
from hhs_nofo_metrics.adapters import (
    AdapterCoverage,
    AdapterDescriptor,
    AdapterEvidence,
    AdapterRegistry,
    AdapterResult,
    SupportAssessment,
    canonical_configuration_sha256,
    create_default_registry,
    run_adapter_conformance,
    validate_adapter_result,
)
from hhs_nofo_metrics.models import NormalizedDocument, Segment, SourceLocation
from hhs_nofo_metrics.sources import materialize_source_bundle

CLI = (sys.executable, "-m", "hhs_nofo_metrics_cli")


def write_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with path.open("wb") as stream:
        writer.write(stream)


class SyntheticPlugin:
    descriptor = AdapterDescriptor(
        id="synthetic-adapter",
        version="1.0.0",
        source_kinds=("text",),
        auxiliary_kinds=("json",),
        capabilities=frozenset({"text", "logical_roles", "reading_order"}),
        distribution="synthetic-package",
        distribution_version="1.2.3",
    )

    def inspect_support(self, source) -> SupportAssessment:
        return SupportAssessment(
            status="supported",
            evidence=(
                AdapterEvidence(
                    code="synthetic_kind",
                    value=source.primary.kind,
                    confidence="high",
                ),
            ),
        )

    def extract(self, source, *, config) -> AdapterResult:
        document = NormalizedDocument(
            source_kind=source.primary.kind,
            source_sha256=source.primary.sha256,
            adapter_id=self.descriptor.id,
            adapter_version=self.descriptor.version,
            segments=(
                Segment(
                    id="segment-1",
                    text="Synthetic source sentence.",
                    location=SourceLocation(),
                    reading_order=0,
                    role="body",
                    role_confidence="high",
                    role_basis="synthetic_plugin",
                ),
            ),
        )
        return AdapterResult(
            document=document,
            artifacts_consumed=tuple(artifact.name for artifact in source.artifacts),
            capabilities_used=self.descriptor.capabilities,
            coverage=AdapterCoverage(status="complete", matched_blocks=1),
            dependencies={"synthetic": "1.0.0"},
        )


def synthetic_bundle() -> SourceBundle:
    return SourceBundle(
        primary=SourceArtifact(name="primary", kind="text", source=b"hello"),
        auxiliaries=(
            SourceArtifact(
                name="builder_manifest",
                kind="json",
                source=b'{"version": 1}',
                media_type="application/json",
            ),
        ),
    )


def test_source_bundle_materializes_hashes_and_restores_stream_position() -> None:
    stream = BytesIO(b"source bytes")
    stream.seek(4)
    bundle = SourceBundle(
        primary=SourceArtifact(name="primary", kind="pdf", source=stream)
    )

    with materialize_source_bundle(bundle) as materialized:
        assert materialized.primary.byte_length == len(b"source bytes")
        assert materialized.primary.sha256 == (
            "4d4823794cbed3c4ee0bbc684c8f66e1dfd5afa6f078d494ce254ec5a4671753"
        )
        assert materialized.primary.path.is_file()

    assert stream.tell() == 4
    assert not materialized.primary.path.exists()


def test_source_bundle_rejects_duplicate_or_invalid_artifact_names() -> None:
    with pytest.raises(ValueError, match="artifact names must be unique"):
        SourceBundle(
            primary=SourceArtifact(name="primary", kind="pdf", source=b"pdf"),
            auxiliaries=(SourceArtifact(name="primary", kind="json", source=b"{}"),),
        )
    with pytest.raises(ValueError, match="artifact name must start"):
        SourceArtifact(name="Builder-Manifest", kind="json", source=b"{}")


def test_path_source_is_snapshotted_before_adapter_execution(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"snapshot bytes")
    bundle = SourceBundle.from_pdf(source)

    with materialize_source_bundle(bundle) as materialized:
        staged_path = materialized.primary.path
        assert staged_path != source.resolve()
        assert staged_path.read_bytes() == b"snapshot bytes"

    assert not staged_path.exists()


def test_adapter_contract_accepts_valid_source_bundle_result() -> None:
    plugin = SyntheticPlugin()
    with materialize_source_bundle(synthetic_bundle()) as materialized:
        result = plugin.extract(materialized, config={})
        validate_adapter_result(plugin, materialized, result)
        assert result.artifacts_consumed == ("primary", "builder_manifest")


def test_synthetic_external_plugin_passes_reusable_conformance_suite() -> None:
    plugin = SyntheticPlugin()
    with materialize_source_bundle(synthetic_bundle()) as materialized:
        report = run_adapter_conformance(plugin, materialized)

    assert report.to_dict() == {
        "adapter_reference": "synthetic-adapter@1.0.0",
        "configuration_sha256": canonical_configuration_sha256({}),
        "checks": [
            "descriptor_valid",
            "source_contract_valid",
            "support_assessment_valid",
            "output_contract_valid",
            "deterministic_output",
            "policy_override_absent",
            "materialized_path_privacy",
        ],
        "conformant": True,
    }


def test_adapter_contract_rejects_policy_override_and_hash_mismatch() -> None:
    plugin = SyntheticPlugin()
    with materialize_source_bundle(synthetic_bundle()) as materialized:
        valid = plugin.extract(materialized, config={})
        overridden = NormalizedDocument(
            source_kind=valid.document.source_kind,
            source_sha256=valid.document.source_sha256,
            adapter_id=valid.document.adapter_id,
            adapter_version=valid.document.adapter_version,
            segments=(
                Segment(
                    id="segment-1",
                    text="text",
                    location=SourceLocation(),
                    reading_order=0,
                    inclusion_override=True,
                ),
            ),
        )
        with pytest.raises(AdapterContractError, match="inclusion_override"):
            validate_adapter_result(
                plugin,
                materialized,
                AdapterResult(
                    document=overridden,
                    artifacts_consumed=("primary",),
                    capabilities_used=frozenset({"text"}),
                    coverage=AdapterCoverage(status="complete"),
                ),
            )

        wrong_hash = NormalizedDocument(
            source_kind=valid.document.source_kind,
            source_sha256="a" * 64,
            adapter_id=valid.document.adapter_id,
            adapter_version=valid.document.adapter_version,
            segments=valid.document.segments,
        )
        with pytest.raises(AdapterContractError, match="hash does not match"):
            validate_adapter_result(
                plugin,
                materialized,
                AdapterResult(
                    document=wrong_hash,
                    artifacts_consumed=("primary",),
                    capabilities_used=frozenset({"text"}),
                    coverage=AdapterCoverage(status="complete"),
                ),
            )

        leaking = replace(
            valid,
            evidence=(
                AdapterEvidence(
                    code="debug_path",
                    value=str(materialized.primary.path),
                    confidence="high",
                ),
            ),
        )
        with pytest.raises(AdapterContractError, match="must not expose"):
            validate_adapter_result(plugin, materialized, leaking)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"artifacts_consumed": ["primary"]}, "must be a tuple"),
        ({"dependencies": ["dependency"]}, "must be a mapping"),
        ({"warnings": ["warning"]}, "warnings must be a tuple"),
        ({"evidence": ["evidence"]}, "evidence must be a tuple"),
    ],
)
def test_adapter_contract_rejects_malformed_result_containers(
    changes: dict[str, object], message: str
) -> None:
    plugin = SyntheticPlugin()
    with materialize_source_bundle(synthetic_bundle()) as materialized:
        result = replace(plugin.extract(materialized, config={}), **changes)
        with pytest.raises(AdapterContractError, match=message):
            validate_adapter_result(plugin, materialized, result)


def test_adapter_contract_rejects_malformed_document_containers() -> None:
    plugin = SyntheticPlugin()
    with materialize_source_bundle(synthetic_bundle()) as materialized:
        valid = plugin.extract(materialized, config={})
        malformed_document = replace(
            valid.document, segments=list(valid.document.segments)
        )
        result = replace(valid, document=malformed_document)

        with pytest.raises(AdapterContractError, match="segments must be a tuple"):
            validate_adapter_result(plugin, materialized, result)


def test_public_adapter_errors_redact_materialized_paths() -> None:
    class PathLeakingPlugin(SyntheticPlugin):
        def inspect_support(self, source) -> SupportAssessment:
            raise RuntimeError(f"inspection failed at {source.primary.path}")

        def extract(self, source, *, config) -> AdapterResult:
            raise RuntimeError(f"extraction failed in {source.primary.path.parent}")

    plugin = PathLeakingPlugin()
    with materialize_source_bundle(synthetic_bundle()) as materialized:
        artifact_path = str(materialized.primary.path)
        directory_path = str(materialized.primary.path.parent)
        with pytest.raises(AdapterExecutionError) as inspection:
            api_module._inspect_support(plugin, materialized)
        with pytest.raises(AdapterExecutionError) as extraction:
            api_module._extract(plugin, materialized, config={})

    inspection_message = str(inspection.value)
    extraction_message = str(extraction.value)
    assert artifact_path not in inspection_message
    assert directory_path not in inspection_message
    assert artifact_path not in extraction_message
    assert directory_path not in extraction_message
    assert "<materialized-artifact>" in inspection_message
    assert "<materialized-directory>" in extraction_message


def test_registry_rejects_duplicates_and_resolves_explicit_versions() -> None:
    plugin = SyntheticPlugin()
    registry = AdapterRegistry(plugins=(plugin,))

    assert registry.resolve("synthetic-adapter") is plugin
    assert registry.resolve("synthetic-adapter@1.0.0") is plugin
    with pytest.raises(AdapterContractError, match="duplicate adapter reference"):
        registry.register(plugin)


def test_configuration_hash_is_canonical_and_rejects_non_json() -> None:
    assert canonical_configuration_sha256({"a": 1, "b": [True]}) == (
        canonical_configuration_sha256({"b": [True], "a": 1})
    )
    with pytest.raises(AdapterContractError, match="not a JSON value"):
        canonical_configuration_sha256({"bad": object()})  # type: ignore[dict-item]
    with pytest.raises(AdapterContractError, match="key at config must be a string"):
        canonical_configuration_sha256({1: "bad"})  # type: ignore[dict-item]


def test_builtin_pdf_analysis_publishes_text_free_plugin_provenance(
    tmp_path: Path,
) -> None:
    source = tmp_path / "fixture.pdf"
    write_pdf(source)

    result = analyze(
        source,
        profile="hhs-nofo-fy27-generic-pdf-estimate@0.4.0",
    )
    payload = result.to_dict()

    assert payload["schema_version"] == "1.2.0"
    assert payload["adapter"]["id"] == "hhs-pdf-adapter"
    assert payload["adapter"]["contract_version"] == "1.0.0"
    assert payload["adapter"]["fallback_history"] == []
    assert payload["adapter"]["configuration_sha256"] == (
        canonical_configuration_sha256({})
    )
    assert payload["source"]["artifacts"] == [
        {
            "name": "primary",
            "kind": "pdf",
            "sha256": result.source.sha256,
            "byte_length": source.stat().st_size,
            "media_type": "application/pdf",
        }
    ]
    serialized = json.dumps(payload)
    assert str(tmp_path) not in serialized
    assert '"segments"' not in serialized


def test_adapter_inspection_is_advisory_and_generic_pdf_rejects_auxiliary(
    tmp_path: Path,
) -> None:
    source = tmp_path / "fixture.pdf"
    write_pdf(source)

    assessments = inspect_adapter_support(source, adapter="pdf")
    assert assessments[0]["assessment"]["status"] == "supported"
    assert any(
        item["reference"].startswith("hhs-pdf-adapter@") for item in list_adapters()
    )

    bundle = SourceBundle(
        primary=SourceArtifact(name="primary", kind="pdf", source=source),
        auxiliaries=(SourceArtifact(name="manifest", kind="json", source=b"{}"),),
    )
    with pytest.raises(AdapterContractError, match="auxiliary artifacts"):
        analyze(
            bundle,
            adapter="pdf",
            profile="hhs-nofo-fy27-generic-pdf-estimate@0.4.0",
        )
    assert (
        inspect_adapter_support(bundle, adapter="pdf")[0]["assessment"]["status"]
        == "unsupported"
    )


def test_default_registry_contains_supported_builtin_adapters() -> None:
    registry = create_default_registry()

    assert registry.resolve("pdf").descriptor.id == "hhs-pdf-adapter"
    assert registry.resolve("tagged-pdf").descriptor.id == "hhs-tagged-pdf-adapter"
    with pytest.raises(AdapterNotFoundError):
        registry.resolve("sentence-pdf")


def test_adapter_cli_lists_and_inspects_without_selecting(tmp_path: Path) -> None:
    source = tmp_path / "fixture.pdf"
    write_pdf(source)

    listed = subprocess.run(
        [*CLI, "adapters", "list", "--json"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert listed.returncode == 0, listed.stderr
    assert any(
        item["reference"] == "hhs-pdf-adapter@0.4.0"
        for item in json.loads(listed.stdout)["adapters"]
    )

    inspected = subprocess.run(
        [
            *CLI,
            "adapters",
            "inspect",
            str(source),
            "--adapter",
            "pdf",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert inspected.returncode == 0, inspected.stderr
    payload = json.loads(inspected.stdout)
    assert payload["selection_performed"] is False
    assert payload["assessments"][0]["assessment"]["status"] == "supported"
