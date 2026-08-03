from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.authority_container import (
    AuthorityArtifact,
    encode_authority_container,
    parse_authority_container,
)
from cuda_fractal_state_tool.finding_enrichment import (
    CommonFindingProvider,
    FindingEnrichmentService,
    ProviderRegistry,
)


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _viewport_facts(selector: str, width: int, height: int) -> dict[str, object]:
    return {
        "schema_version": 1,
        "mapping_id": "cuda_fractal_renderer_pixel_center_v1",
        "selected_fractal_type": selector,
        "render": {"width": width, "height": height, "aspect_ratio": width / height},
        "camera": {
            "center_hp_x": -0.5,
            "center_hp_y": 0.25,
            "log2_zoom": 3.0,
            "resolved_zoom": 8.0,
            "rotation_degrees": 0.0,
        },
        "local_frame": {
            "half_width": 0.125,
            "half_height": 0.075,
            "full_width": 0.25,
            "full_height": 0.15,
        },
        "complex_pixel_basis": {
            "x_step": {"real": 0.001, "imag": 0.0},
            "y_step": {"real": 0.0, "imag": -0.001},
            "units_per_pixel_x": 0.001,
            "units_per_pixel_y": 0.001,
        },
        "continuous_edge_corners": [
            {"real": -0.625, "imag": 0.325},
            {"real": -0.375, "imag": 0.325},
            {"real": -0.375, "imag": 0.175},
            {"real": -0.625, "imag": 0.175},
        ],
        "pixel_center_corners": [
            {"real": -0.6245, "imag": 0.3245},
            {"real": -0.3755, "imag": 0.3245},
            {"real": -0.3755, "imag": 0.1755},
            {"real": -0.6245, "imag": 0.1755},
        ],
        "axis_aligned_complex_bounds": {
            "minimum": {"real": -0.625, "imag": 0.175},
            "maximum": {"real": -0.375, "imag": 0.325},
        },
        "fit_model": {
            "forward_mapping": "engine-owned",
            "pixel_normalization": "pixel centers",
            "inverse_fit": "engine-owned inverse",
            "point_preparation": "none",
        },
    }


def _build_packet(root: Path, *, packet_id: str = "packet-a", selector: str = "explaino_bell") -> Path:
    packet_dir = root / "findings" / "finding-a" / "packets" / packet_id
    packet_dir.mkdir(parents=True)
    state = {
        "state_version": 3,
        "fractal_type": selector,
        "params": {"max_iter": 500, "explaino_damping": 1.0},
        "view": {
            "center_x": -0.5,
            "center_hp_x": -0.5,
            "center_y": 0.25,
            "center_hp_y": 0.25,
            "zoom": 8.0,
            "log2_zoom": 3.0,
        },
        "render": {"width": 320, "height": 200, "device_id": 0},
    }
    payloads = {
        "state.json": _json_bytes(state),
        "state-override-authoring-surface.json": _json_bytes(
            {"surface_version": 2, "entries": []}
        ),
        "fractal_binding_surface_v1.ui_schema.json": _json_bytes({"schema_version": 1}),
        "fractal-parameter-surface.json": _json_bytes({"schema_version": 1}),
        "color_pipeline_function_library.contract.v1.json": _json_bytes({"contract_version": 1}),
        "fractal-descriptive-catalog.json": _json_bytes({"schema_version": 1, "entries": []}),
        "fractal-viewport-facts.json": _json_bytes(_viewport_facts(selector, 320, 200)),
        "fractal-state.json": _json_bytes({"schema": "viewer.finding_fractal_state.v1"}),
    }
    containers = {
        "state-authoring-authorities.md": encode_authority_container(
            "State authoring",
            "Exact test authorities.",
            (
                AuthorityArtifact(
                    "state-override-authoring-surface.json",
                    "finding-specific mechanically derived state-override index",
                    "application/json",
                    payloads["state-override-authoring-surface.json"],
                ),
                AuthorityArtifact(
                    "fractal_binding_surface_v1.ui_schema.json",
                    "exact deployed UI control and serialized state-binding authority",
                    "application/json",
                    payloads["fractal_binding_surface_v1.ui_schema.json"],
                ),
                AuthorityArtifact(
                    "fractal-parameter-surface.json",
                    "exact runtime-selected parameter applicability authority",
                    "application/json",
                    payloads["fractal-parameter-surface.json"],
                ),
            ),
        ),
        "color-pipeline-authority.md": encode_authority_container(
            "Color authority",
            "Exact test authority.",
            (
                AuthorityArtifact(
                    "color_pipeline_function_library.contract.v1.json",
                    "exact deployed Color Pipeline function and compatibility authority",
                    "application/json",
                    payloads["color_pipeline_function_library.contract.v1.json"],
                ),
            ),
        ),
        "finding-context.md": encode_authority_container(
            "Finding context",
            "Exact test context.",
            (
                AuthorityArtifact(
                    "fractal-viewport-facts.json",
                    "exact engine-owned viewport geometry and inverse-fit authority",
                    "application/json",
                    payloads["fractal-viewport-facts.json"],
                ),
                AuthorityArtifact(
                    "fractal-state.json",
                    "exact capture-time review projection and derived receipts",
                    "application/json",
                    payloads["fractal-state.json"],
                ),
                AuthorityArtifact(
                    "fractal-descriptive-catalog.json",
                    "complete exact engine-owned descriptive catalog appendix",
                    "application/json",
                    payloads["fractal-descriptive-catalog.json"],
                ),
            ),
        ),
    }
    physical = {
        "packet.md": b"# Test Packet V8\n",
        "state.json": payloads["state.json"],
        **containers,
    }
    for name, payload in physical.items():
        (packet_dir / name).write_bytes(payload)

    embedded = []
    for container_name, container_bytes in containers.items():
        for artifact in parse_authority_container(container_bytes).artifacts.values():
            embedded.append(
                {
                    "container_path": container_name,
                    "artifact_filename": artifact.filename,
                    "authority_role": artifact.role,
                    "media_type": artifact.media_type,
                    "encoding": artifact.encoding,
                    "size_bytes": artifact.byte_length,
                    "sha256": artifact.sha256,
                    "record_id": artifact.record_id,
                }
            )
    required = [
        "packet.md",
        "manifest.json",
        "state.json",
        "state-authoring-authorities.md",
        "color-pipeline-authority.md",
        "finding-context.md",
    ]
    manifest = {
        "authority_container_version": 1,
        "authority_identities": {
            "state_sha256": _sha256(payloads["state.json"]),
            "parameter_surface_sha256": _sha256(payloads["fractal-parameter-surface.json"]),
            "ui_schema_sha256": _sha256(payloads["fractal_binding_surface_v1.ui_schema.json"]),
            "ui_salt_contract_sha256": _sha256(
                payloads["color_pipeline_function_library.contract.v1.json"]
            ),
            "fractal_descriptive_catalog_sha256": _sha256(
                payloads["fractal-descriptive-catalog.json"]
            ),
            "fractal_viewport_facts_sha256": _sha256(payloads["fractal-viewport-facts.json"]),
            "state_override_authoring_surface_sha256": _sha256(
                payloads["state-override-authoring-surface.json"]
            ),
        },
        "bundle_manifest_version": 4,
        "drag_all_attachments": required,
        "embedded_artifacts": embedded,
        "files": [
            {
                "path": name,
                "role": "test",
                "sha256": _sha256(payload),
                "size_bytes": len(payload),
                "web_handoff": "required",
            }
            for name, payload in physical.items()
        ],
        "finding_id": "finding-a",
        "packet_id": packet_id,
        "packet_version": 8,
        "recommended_attachments": [],
        "required_attachments": required,
        "runtime_identity": {
            "launcher_sha256": "1" * 64,
            "resolved_executable_sha256": "2" * 64,
            "resolved_executable_file_version": "",
            "runtime_schema_sha256": "3" * 64,
            "ui_salt_contract_sha256": _sha256(
                payloads["color_pipeline_function_library.contract.v1.json"]
            ),
        },
        "runtime_identity_sha256": "4" * 64,
        "selected_fractal_description_status": "unavailable",
        "selected_fractal_type": selector,
        "unavailable_optional_attachments": [],
    }
    (packet_dir / "manifest.json").write_bytes(_json_bytes(manifest))
    return packet_dir


class _SyntheticProvider:
    provider_id = "synthetic.v1"
    provider_version = 1
    supported_model_ids = ("synthetic.model.v1",)


class FindingEnrichmentTests(unittest.TestCase):
    def test_registry_rejects_duplicate_provider_or_model_ownership(self) -> None:
        registry = ProviderRegistry()
        registry.register(_SyntheticProvider())
        with self.assertRaisesRegex(ValueError, "provider ID"):
            registry.register(_SyntheticProvider())

        class RepeatingProvider:
            provider_id = "repeating.v1"
            provider_version = 1
            supported_model_ids = ("repeat.model.v1", "repeat.model.v1")

        with self.assertRaisesRegex(ValueError, "repeats a model ID"):
            registry.register(RepeatingProvider())

        class ConflictingProvider:
            provider_id = "other.v1"
            provider_version = 1
            supported_model_ids = ("synthetic.model.v1",)

        with self.assertRaisesRegex(ValueError, "model ID"):
            registry.register(ConflictingProvider())

    def test_common_enrichment_is_immutable_deterministic_and_model_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            packet = _build_packet(workspace)
            before = {path.name: path.read_bytes() for path in packet.iterdir()}
            service = FindingEnrichmentService(
                workspace_root=workspace,
                common_provider=CommonFindingProvider(),
                model_registry=ProviderRegistry(),
            )

            first = service.analyze(packet)
            second = service.analyze(packet)

            self.assertEqual(first.analysis_id, second.analysis_id)
            self.assertEqual(first.analysis_dir, second.analysis_dir)
            self.assertFalse(first.cache_hit)
            self.assertTrue(second.cache_hit)
            self.assertEqual(before, {path.name: path.read_bytes() for path in packet.iterdir()})
            self.assertEqual(first.analysis_dir.parent.parent.name, "finding-a")
            common = json.loads((first.analysis_dir / "common-facts.json").read_text(encoding="utf-8"))
            self.assertEqual(common["selected_fractal_type"], "explaino_bell")
            self.assertEqual(common["render"]["width"], 320)
            self.assertEqual(
                common["viewport"]["axis_aligned_complex_bounds"]["minimum"]["real"],
                -0.625,
            )
            self.assertEqual(common["epistemic_status"], "exact_packet_fact")
            unavailable = json.loads(
                (first.analysis_dir / "provider-result.json").read_text(encoding="utf-8")
            )
            self.assertEqual(unavailable["status"], "unavailable")
            self.assertEqual(unavailable["reason"], "active_model_receipt_not_supplied")
            receipt = json.loads((first.analysis_dir / "receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["analysis_id"], first.analysis_id)
            self.assertEqual(receipt["artifact_sha256"]["common-facts.json"], _sha256(
                (first.analysis_dir / "common-facts.json").read_bytes()
            ))

    def test_changed_packet_bytes_fail_closed_and_existing_analysis_tampering_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            packet = _build_packet(workspace)
            service = FindingEnrichmentService(workspace_root=workspace)
            result = service.analyze(packet)
            (result.analysis_dir / "common-facts.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "(?i)existing analysis artifact changed"):
                service.analyze(packet)

            other_packet = _build_packet(workspace, packet_id="packet-b")
            (other_packet / "state.json").write_bytes(b"{}\n")
            with self.assertRaisesRegex(ValueError, "changed after publication"):
                service.analyze(other_packet)


if __name__ == "__main__":
    unittest.main()
