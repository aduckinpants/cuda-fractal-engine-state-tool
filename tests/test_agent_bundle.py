from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cuda_fractal_state_tool.agent_bundle import (
    _validate_color_pipeline_compatibility_authority,
    build_agent_bundle,
    copy_agent_packet,
    derive_state_override_authoring_surface,
    load_agent_bundle_handoff,
    open_agent_bundle_folder,
    validate_captured_color_pipeline_draft,
)
from cuda_fractal_state_tool.agent_bundle_cli import main as agent_bundle_cli_main
from cuda_fractal_state_tool.finding_workspace import SourceCaptureImporter


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


class AgentBundleTests(unittest.TestCase):
    def _fixture(self, root: Path):
        capture = root / "capture"
        capture.mkdir()
        state = {
            "state_version": 3,
            "fractal_type": "explaino_all",
            "params": {
                "max_iter": 500,
                "explaino_damping": 1.0,
                "exposure": 1.0,
                "color_glow": 0.75,
                "mode": "active",
            },
            "view": {
                "center_x": -0.5,
                "center_hp_x": -0.5,
                "center_y": 0.0,
                "center_hp_y": 0.0,
                "zoom": 4.0,
                "log2_zoom": 2.0,
            },
            "render": {"width": 640, "height": 480, "device_id": 0},
            "color_pipeline_draft": {
                "next_row_id": 5,
                "lanes": [
                    {
                        "lane_id": "source",
                        "label": "Source",
                        "rows": [
                            {
                                "ui_row_id": 1,
                                "enabled": True,
                                "function_id": "identity",
                                "parameter_values": [],
                            }
                        ],
                    },
                    {
                        "lane_id": "shape",
                        "label": "Shape",
                        "rows": [
                            {
                                "ui_row_id": 2,
                                "enabled": True,
                                "function_id": "identity",
                                "parameter_values": [],
                            }
                        ],
                    },
                    {
                        "lane_id": "palette",
                        "label": "Palette",
                        "rows": [
                            {
                                "ui_row_id": 3,
                                "enabled": True,
                                "function_id": "identity",
                                "parameter_values": [],
                            }
                        ],
                    },
                    {
                        "lane_id": "grading",
                        "label": "Grading",
                        "rows": [
                            {
                                "ui_row_id": 4,
                                "enabled": True,
                                "function_id": "contrast_lift",
                                "parameter_values": [
                                    {"path": "grade.saturation", "type": "float", "number_value": 1.0}
                                ],
                            }
                        ],
                    },
                ],
            },
        }
        state_bytes = _json_bytes(state)
        (capture / "state.json").write_bytes(state_bytes)
        review_bytes = _json_bytes({"schema_id": "viewer.finding_fractal_state.v1"})
        (capture / "fractal-state.json").write_bytes(review_bytes)
        finding_bytes = _json_bytes({"finding_schema_version": 1})
        (capture / "finding.json").write_bytes(finding_bytes)
        notes_bytes = b"A user-authored note.\r\n"
        (capture / "field-notes.md").write_bytes(notes_bytes)
        frame_bytes = b"not-a-real-png-but-exact-capture-bytes"
        (capture / "frame.png").write_bytes(frame_bytes)

        parameter_surface = {
            "version": 1,
            "lanes": [
                {
                    "fractal_id": "explaino_all",
                    "controls": [
                        {
                            "control_id": "explaino_damping",
                            "binding_path": "fractal.params.explaino_damping",
                            "binding_resolves": True,
                            "state_io_key": "explaino_damping",
                            "default_visible": True,
                        },
                        {
                            "control_id": "live_root_pattern",
                            "binding_path": "fractal.root_pattern.dynamics.scale",
                            "binding_resolves": True,
                            "state_io_key": "",
                            "default_visible": True,
                        },
                        {
                            "control_id": "hidden_control",
                            "binding_path": "fractal.params.mode",
                            "binding_resolves": True,
                            "state_io_key": "mode",
                            "default_visible": False,
                        },
                    ],
                }
            ],
        }
        ui_schema = {
            "schema_version": 1,
            "panels": [
                {
                    "id": "fractal",
                    "controls": [
                        {
                            "id": "explaino_damping",
                            "value_type": "float",
                            "min": 0.01,
                            "max": 10.0,
                            "binding": {"kind": "param", "path": "fractal.params.explaino_damping"},
                        },
                        {
                            "id": "live_root_pattern",
                            "value_type": "float",
                            "binding": {"kind": "param", "path": "fractal.root_pattern.dynamics.scale"},
                        },
                        {
                            "id": "hidden_control",
                            "value_type": "enum",
                            "options": [{"id": "active"}],
                            "binding": {"kind": "param", "path": "fractal.params.mode"},
                        },
                        {
                            "id": "exposure",
                            "value_type": "float",
                            "min": 0.0,
                            "max": 4.0,
                            "binding": {"kind": "param", "path": "fractal.params.exposure"},
                        },
                        {
                            "id": "center_x",
                            "value_type": "float",
                            "binding": {"kind": "param", "path": "fractal.view.center_x"},
                        },
                        {
                            "id": "center_y",
                            "value_type": "float",
                            "binding": {"kind": "param", "path": "fractal.view.center_y"},
                        },
                        {
                            "id": "zoom",
                            "value_type": "float",
                            "min": 0.000001,
                            "binding": {"kind": "param", "path": "fractal.view.zoom"},
                        },
                    ]
                }
            ],
        }
        schema_controls = ui_schema["panels"][0]["controls"]
        exposure_control = next(control for control in schema_controls if control["id"] == "exposure")
        ui_schema["panels"][0]["controls"] = [
            control for control in schema_controls if control["id"] != "exposure"
        ]
        ui_schema["panels"].append({"id": "color", "controls": [exposure_control]})
        contract = {
            "schema_version": 1,
            "composition_recipe_contract": {
                "compatibility": [
                    {
                        "source": "identity",
                        "palette": "identity",
                        "grading": "contrast_lift",
                    }
                ]
            },
            "function_library": {
                "lanes": [
                    {"id": lane, "functions": [{"id": "identity", "params": []}]}
                    for lane in ("source", "shape", "palette")
                ]
                + [
                    {
                        "id": "grading",
                        "functions": [
                            {
                                "id": "contrast_lift",
                                "params": [
                                    {
                                        "path": "grade.saturation",
                                        "type": "float",
                                        "min": 0.0,
                                        "max": 2.0,
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
        }
        catalog = {
            "schema_version": 1,
            "entries": [
                {
                    "selector_id": "explaino_all",
                    "display_name": "ExplainO All",
                    "category": "ExplainO",
                    "family": "ExplainO",
                    "formula_growth_surface": "bounded",
                    "capability_flags": [],
                    "runtime_flags": [],
                    "description_status": "reviewed",
                    "description": {
                        "math_summary": "A reviewed summary.",
                        "recurrence_or_field_model": "A reviewed model.",
                        "state_order": "A reviewed order.",
                        "termination_or_classification": "A reviewed termination rule.",
                        "interpretation_notes": "Reviewed interpretation guidance.",
                        "source_refs": ["src/fractal_registry.cpp#explaino_all"],
                    },
                }
            ],
        }
        viewport_facts = {
            "schema_version": 1,
            "mapping_id": "cuda_fractal_renderer_pixel_center_v1",
            "selected_fractal_type": "explaino_all",
            "render": {"width": 640, "height": 480, "aspect_ratio": 4.0 / 3.0},
            "camera": {
                "center_hp_x": -0.5,
                "center_hp_y": 0.0,
                "log2_zoom": 2.0,
                "resolved_zoom": 4.0,
                "rotation_degrees": 0.0,
            },
            "local_frame": {
                "half_width": 2.0 / 3.0,
                "half_height": 0.5,
                "full_width": 4.0 / 3.0,
                "full_height": 1.0,
            },
            "complex_pixel_basis": {
                "x_step": {"real": 0.0020833333333333333, "imag": 0.0},
                "y_step": {"real": 0.0, "imag": 0.0020833333333333333},
                "units_per_pixel_x": 0.0020833333333333333,
                "units_per_pixel_y": 0.0020833333333333333,
            },
            "continuous_edge_corners": [
                {"real": -1.1666666666666665, "imag": -0.5},
                {"real": 0.16666666666666663, "imag": -0.5},
                {"real": 0.16666666666666663, "imag": 0.5},
                {"real": -1.1666666666666665, "imag": 0.5},
            ],
            "pixel_center_corners": [
                {"real": -1.165625, "imag": -0.49895833333333334},
                {"real": 0.165625, "imag": -0.49895833333333334},
                {"real": 0.165625, "imag": 0.49895833333333334},
                {"real": -1.165625, "imag": 0.49895833333333334},
            ],
            "axis_aligned_complex_bounds": {
                "minimum": {"real": -1.1666666666666665, "imag": -0.5},
                "maximum": {"real": 0.16666666666666663, "imag": 0.5},
            },
            "fit_model": {
                "forward_mapping": "engine mapping",
                "pixel_normalization": "engine normalization",
                "inverse_fit": "engine inverse fit",
                "point_preparation": "engine point preparation",
            },
        }
        runtime = root / "runtime"
        (runtime / "ui").mkdir(parents=True)
        (runtime / "ui_salt" / "generated").mkdir(parents=True)
        runtime_cmd = runtime / "fractal_ui.cmd"
        runtime_cmd.write_bytes(b"@echo off\r\n")
        schema_path = runtime / "ui" / "fractal_binding_surface_v1.ui_schema.json"
        contract_path = runtime / "ui_salt" / "generated" / "color_pipeline_function_library.contract.v1.json"
        schema_path.write_bytes(_json_bytes(ui_schema))
        contract_path.write_bytes(_json_bytes(contract))
        exe = runtime / "fractal_ui.exe"
        exe.write_bytes(b"fake-exe")
        identity = {
            "launcher_sha256": hashlib.sha256(runtime_cmd.read_bytes()).hexdigest(),
            "resolved_executable_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
            "resolved_executable_file_version": "1.2.3.4",
            "runtime_schema_sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest(),
            "ui_salt_contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        }
        resolution = SimpleNamespace(
            runtime_schema_path=str(schema_path),
            ui_salt_contract_path=str(contract_path),
        )
        return {
            "capture": capture,
            "state": state,
            "state_bytes": state_bytes,
            "review_bytes": review_bytes,
            "finding_bytes": finding_bytes,
            "notes_bytes": notes_bytes,
            "frame_bytes": frame_bytes,
            "surface_bytes": _json_bytes(parameter_surface),
            "schema_bytes": schema_path.read_bytes(),
            "contract_bytes": contract_path.read_bytes(),
            "catalog_bytes": _json_bytes(catalog),
            "viewport_facts_bytes": _json_bytes(viewport_facts),
            "runtime_cmd": runtime_cmd,
            "identity": identity,
            "resolution": resolution,
        }

    def test_authoring_surface_is_mechanically_derived_and_excludes_live_only_controls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = self._fixture(Path(temp_dir))
            surface = derive_state_override_authoring_surface(
                fixture["state_bytes"], fixture["surface_bytes"], fixture["schema_bytes"]
            )
            by_path = {entry["path"]: entry for entry in surface["entries"]}
            self.assertIn("params.explaino_damping", by_path)
            self.assertNotIn("params.exposure", by_path)
            self.assertIn("view.center_x", by_path)
            self.assertEqual(by_path["view.center_x"]["companion_paths"], ["view.center_hp_x"])
            self.assertNotIn("params.color_glow", by_path)
            self.assertFalse(any(entry["source_control_id"] == "live_root_pattern" for entry in surface["entries"]))
            self.assertFalse(any(entry["source_control_id"] == "hidden_control" for entry in surface["entries"]))
            self.assertEqual(
                surface["authority_refs"]["parameter_surface_sha256"],
                hashlib.sha256(fixture["surface_bytes"]).hexdigest(),
            )
            self.assertEqual(surface["surface_version"], 2)
            self.assertEqual(surface["color_authoring"]["mode"], "color_pipeline_draft_only")
            self.assertEqual(surface["color_authoring"]["excluded_ui_panel_id"], "color")
            self.assertEqual(
                surface["color_authoring"]["compatibility_authority"],
                "color_pipeline_function_library.contract.v1.json"
                "#/composition_recipe_contract/compatibility",
            )
            self.assertTrue(surface["color_authoring"]["engine_materialization_is_final_authority"])

    def test_pipeline_example_validation_enforces_contract_carrier_range_and_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = self._fixture(Path(temp_dir))
            contract = json.loads(fixture["contract_bytes"])
            self.assertIsNotNone(validate_captured_color_pipeline_draft(fixture["state"], contract))

            bad_state = json.loads(json.dumps(fixture["state"]))
            value = bad_state["color_pipeline_draft"]["lanes"][3]["rows"][0]["parameter_values"][0]
            value["number_value"] = 4.0
            with self.assertRaisesRegex(ValueError, "above the copied range"):
                validate_captured_color_pipeline_draft(bad_state, contract)

            value["number_value"] = 1.0
            value["enum_value"] = "wrong-carrier"
            with self.assertRaisesRegex(ValueError, "wrong numeric carrier"):
                validate_captured_color_pipeline_draft(bad_state, contract)

            missing_compatibility = json.loads(json.dumps(contract))
            missing_compatibility.pop("composition_recipe_contract")
            with self.assertRaisesRegex(ValueError, "composition_recipe_contract"):
                _validate_color_pipeline_compatibility_authority(missing_compatibility)

    def test_build_bundle_preserves_exact_artifacts_and_publishes_coherent_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = self._fixture(root)
            imported = SourceCaptureImporter(root / "workspace").import_capture(fixture["capture"])
            exports = [
                fixture["surface_bytes"],
                fixture["catalog_bytes"],
                fixture["viewport_facts_bytes"],
                fixture["surface_bytes"],
                fixture["catalog_bytes"],
                fixture["viewport_facts_bytes"],
            ]
            with (
                patch("cuda_fractal_state_tool.agent_bundle.resolve_launcher", return_value=fixture["resolution"]),
                patch("cuda_fractal_state_tool.agent_bundle.build_runtime_identity", return_value=fixture["identity"]),
                patch("cuda_fractal_state_tool.agent_bundle._capture_export", side_effect=exports),
            ):
                bundle = build_agent_bundle(imported.finding_dir, fixture["runtime_cmd"])

            self.assertEqual((bundle.packet_dir / "state.json").read_bytes(), fixture["state_bytes"])
            self.assertEqual((bundle.packet_dir / "fractal-state.json").read_bytes(), fixture["review_bytes"])
            self.assertEqual((bundle.packet_dir / "finding.json").read_bytes(), fixture["finding_bytes"])
            self.assertEqual((bundle.packet_dir / "field-notes.md").read_bytes(), fixture["notes_bytes"])
            self.assertEqual((bundle.packet_dir / "frame.png").read_bytes(), fixture["frame_bytes"])

            manifest = json.loads(bundle.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["packet_version"], 6)
            self.assertEqual(manifest["bundle_manifest_version"], 2)
            recorded = {item["path"]: item for item in manifest["files"]}
            actual = {path.name for path in bundle.packet_dir.iterdir() if path.name != "manifest.json"}
            self.assertEqual(set(recorded), actual)
            for name, item in recorded.items():
                payload = (bundle.packet_dir / name).read_bytes()
                self.assertEqual(item["sha256"], hashlib.sha256(payload).hexdigest())
                self.assertEqual(item["size_bytes"], len(payload))
            self.assertNotIn("manifest.json", recorded)

            surface = json.loads((bundle.packet_dir / "state-override-authoring-surface.json").read_text())
            self.assertEqual(
                surface["authority_refs"]["ui_schema_sha256"],
                hashlib.sha256((bundle.packet_dir / "fractal_binding_surface_v1.ui_schema.json").read_bytes()).hexdigest(),
            )
            packet = bundle.packet_path.read_text(encoding="utf-8")
            self.assertIn("State Override Example", packet)
            self.assertIn("Dynamics and viewport continuity", packet)
            self.assertIn("same_window_comparison", packet)
            self.assertIn("feature_tracking", packet)
            self.assertIn("transition_survey", packet)
            self.assertIn("Small numerical changes do not establish small visual changes", packet)
            self.assertIn("Chosen experiment", packet)
            self.assertIn("Why this override", packet)
            self.assertIn("Expected effect and uncertainty", packet)
            self.assertIn("Camera intent and viewport check", packet)
            self.assertIn("Hostile self-review conclusion", packet)
            self.assertIn("A sweep cannot be encoded as one override", packet)
            self.assertIn("Generic assent", packet)
            self.assertIn("predicted to intersect the exact retained viewport", packet)
            self.assertIn("intentionally expected to lose the subject", packet)
            self.assertIn("Do not provide private chain-of-thought", packet)
            self.assertIn("no other code block", packet)
            self.assertIn("fractal-viewport-facts.json", bundle.required_attachments)
            self.assertEqual(
                manifest["authority_identities"]["fractal_viewport_facts_sha256"],
                hashlib.sha256(fixture["viewport_facts_bytes"]).hexdigest(),
            )
            self.assertEqual(manifest["viewport_facts_origin"], "runtime_export_from_copied_state")
            self.assertIn("Copying this Markdown does not transport those files", packet)
            self.assertNotIn("proposal_v1", packet)
            self.assertNotIn("capability_profile", packet)
            self.assertNotIn("select_function", packet)
            self.assertNotIn("`params.exposure`", packet)
            self.assertIn("color authoring is Color-Pipeline-only", packet)
            self.assertIn("Do not return flat `params` color controls", packet)
            self.assertIn("Function IDs are not freely composable", packet)
            self.assertIn("composition_recipe_contract.compatibility", packet)
            self.assertIn("Contract-valid drafts outside a runtime-supported recipe", packet)
            self.assertIn("applies that loaded draft through the engine-owned lowering operation", packet)
            self.assertIn("unchanged structural template", packet)
            self.assertNotIn("pending editor state", packet)
            self.assertNotIn("state-override-example-color-pipeline.json", bundle.required_attachments)
            self.assertIn("state-override-example-color-pipeline.json", bundle.recommended_attachments)

            copied: list[str] = []
            handoff = copy_agent_packet(bundle.packet_dir, copied.append)
            self.assertEqual(copied, [packet])
            opened: list[Path] = []
            open_agent_bundle_folder(bundle.packet_dir, opened.append)
            self.assertEqual(opened, [bundle.packet_dir])
            self.assertEqual(load_agent_bundle_handoff(bundle.packet_dir), handoff)

            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(
                    agent_bundle_cli_main(["inspect", "--packet-dir", str(bundle.packet_dir)]),
                    0,
                )
            cli_result = json.loads(stdout.getvalue())
            self.assertEqual(cli_result["packet_sha256"], bundle.packet_sha256)
            self.assertEqual(cli_result["required_attachments"], list(bundle.required_attachments))

    def test_cli_reports_structured_bundle_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing-packet"
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = agent_bundle_cli_main(["inspect", "--packet-dir", str(missing)])
            self.assertEqual(exit_code, 2)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "bundle_error")
            self.assertEqual(payload["operation"], "inspect")
            self.assertIn("missing", payload["error"].lower())

    def test_runtime_identity_change_discards_staged_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = self._fixture(root)
            imported = SourceCaptureImporter(root / "workspace").import_capture(fixture["capture"])
            changed_identity = dict(fixture["identity"])
            changed_identity["resolved_executable_sha256"] = "f" * 64
            with (
                patch("cuda_fractal_state_tool.agent_bundle.resolve_launcher", return_value=fixture["resolution"]),
                patch(
                    "cuda_fractal_state_tool.agent_bundle.build_runtime_identity",
                    side_effect=[fixture["identity"], changed_identity],
                ),
                patch(
                    "cuda_fractal_state_tool.agent_bundle._capture_export",
                    side_effect=[
                        fixture["surface_bytes"],
                        fixture["catalog_bytes"],
                        fixture["viewport_facts_bytes"],
                        fixture["surface_bytes"],
                        fixture["catalog_bytes"],
                        fixture["viewport_facts_bytes"],
                    ],
                ),
            ):
                with self.assertRaisesRegex(ValueError, "runtime identity changed"):
                    build_agent_bundle(imported.finding_dir, fixture["runtime_cmd"])
            packets_dir = imported.finding_dir / "packets"
            self.assertEqual(list(packets_dir.iterdir()), [])

    def test_source_change_during_final_runtime_recheck_discards_staged_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = self._fixture(root)
            imported = SourceCaptureImporter(root / "workspace").import_capture(fixture["capture"])
            source_state = imported.finding_dir / "source" / "state.json"
            exports = [
                fixture["surface_bytes"],
                fixture["catalog_bytes"],
                fixture["viewport_facts_bytes"],
                fixture["surface_bytes"],
                fixture["catalog_bytes"],
                fixture["viewport_facts_bytes"],
            ]

            def changing_export(*_args, **_kwargs):
                result = exports.pop(0)
                if len(exports) == 1:
                    source_state.write_bytes(source_state.read_bytes() + b" ")
                return result

            with (
                patch("cuda_fractal_state_tool.agent_bundle.resolve_launcher", return_value=fixture["resolution"]),
                patch("cuda_fractal_state_tool.agent_bundle.build_runtime_identity", return_value=fixture["identity"]),
                patch("cuda_fractal_state_tool.agent_bundle._capture_export", side_effect=changing_export),
            ):
                with self.assertRaisesRegex(ValueError, "Finding source changed"):
                    build_agent_bundle(imported.finding_dir, fixture["runtime_cmd"])
            packets_dir = imported.finding_dir / "packets"
            self.assertEqual(list(packets_dir.iterdir()), [])

    def test_missing_optional_files_are_reported_not_implied(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = self._fixture(root)
            for filename in ("finding.json", "fractal-state.json", "field-notes.md", "frame.png"):
                (fixture["capture"] / filename).unlink()
            state = json.loads((fixture["capture"] / "state.json").read_text())
            state.pop("color_pipeline_draft")
            (fixture["capture"] / "state.json").write_bytes(_json_bytes(state))
            imported = SourceCaptureImporter(root / "workspace").import_capture(fixture["capture"])
            with (
                patch("cuda_fractal_state_tool.agent_bundle.resolve_launcher", return_value=fixture["resolution"]),
                patch("cuda_fractal_state_tool.agent_bundle.build_runtime_identity", return_value=fixture["identity"]),
                patch(
                    "cuda_fractal_state_tool.agent_bundle._capture_export",
                    side_effect=[
                        fixture["surface_bytes"],
                        fixture["catalog_bytes"],
                        fixture["viewport_facts_bytes"],
                        fixture["surface_bytes"],
                        fixture["catalog_bytes"],
                        fixture["viewport_facts_bytes"],
                    ],
                ),
            ):
                bundle = build_agent_bundle(imported.finding_dir, fixture["runtime_cmd"])
            self.assertEqual(bundle.recommended_attachments, ())
            self.assertEqual(
                bundle.unavailable_optional_attachments,
                ("fractal-state.json", "finding.json", "field-notes.md", "frame"),
            )
            packet = bundle.packet_path.read_text(encoding="utf-8")
            self.assertIn("- `field-notes.md`", packet)
            self.assertIn("Color Pipeline state override authoring is unavailable", packet)
            self.assertFalse((bundle.packet_dir / "state-override-example-color-pipeline.json").exists())
            surface = json.loads(
                (bundle.packet_dir / "state-override-authoring-surface.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(surface["color_authoring"]["mode"], "unavailable")
            self.assertNotIn("params.exposure", {entry["path"] for entry in surface["entries"]})

    def test_handoff_rejects_attachment_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = self._fixture(root)
            imported = SourceCaptureImporter(root / "workspace").import_capture(fixture["capture"])
            with (
                patch("cuda_fractal_state_tool.agent_bundle.resolve_launcher", return_value=fixture["resolution"]),
                patch("cuda_fractal_state_tool.agent_bundle.build_runtime_identity", return_value=fixture["identity"]),
                patch(
                    "cuda_fractal_state_tool.agent_bundle._capture_export",
                    side_effect=[
                        fixture["surface_bytes"],
                        fixture["catalog_bytes"],
                        fixture["viewport_facts_bytes"],
                        fixture["surface_bytes"],
                        fixture["catalog_bytes"],
                        fixture["viewport_facts_bytes"],
                    ],
                ),
            ):
                bundle = build_agent_bundle(imported.finding_dir, fixture["runtime_cmd"])
            (bundle.packet_dir / "state.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed after publication"):
                load_agent_bundle_handoff(bundle.packet_dir)

    def test_capture_viewport_sidecar_is_preserved_only_when_runtime_reproduces_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = self._fixture(root)
            (fixture["capture"] / "fractal-viewport-facts.json").write_bytes(
                fixture["viewport_facts_bytes"]
            )
            imported = SourceCaptureImporter(root / "workspace").import_capture(fixture["capture"])
            exports = [
                fixture["surface_bytes"],
                fixture["catalog_bytes"],
                fixture["viewport_facts_bytes"],
                fixture["surface_bytes"],
                fixture["catalog_bytes"],
                fixture["viewport_facts_bytes"],
            ]
            with (
                patch("cuda_fractal_state_tool.agent_bundle.resolve_launcher", return_value=fixture["resolution"]),
                patch("cuda_fractal_state_tool.agent_bundle.build_runtime_identity", return_value=fixture["identity"]),
                patch("cuda_fractal_state_tool.agent_bundle._capture_export", side_effect=exports),
            ):
                bundle = build_agent_bundle(imported.finding_dir, fixture["runtime_cmd"])

            self.assertEqual(
                (bundle.packet_dir / "fractal-viewport-facts.json").read_bytes(),
                fixture["viewport_facts_bytes"],
            )
            manifest = json.loads(bundle.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["viewport_facts_origin"],
                "captured_finding_sidecar_verified_against_runtime",
            )

            changed = json.loads(fixture["viewport_facts_bytes"])
            changed["mapping_id"] = "stale-mapping"
            (fixture["capture"] / "fractal-viewport-facts.json").write_bytes(_json_bytes(changed))
            stale = SourceCaptureImporter(root / "stale-workspace").import_capture(fixture["capture"])
            with (
                patch("cuda_fractal_state_tool.agent_bundle.resolve_launcher", return_value=fixture["resolution"]),
                patch("cuda_fractal_state_tool.agent_bundle.build_runtime_identity", return_value=fixture["identity"]),
                patch(
                    "cuda_fractal_state_tool.agent_bundle._capture_export",
                    side_effect=[
                        fixture["surface_bytes"],
                        fixture["catalog_bytes"],
                        fixture["viewport_facts_bytes"],
                    ],
                ),
            ):
                with self.assertRaisesRegex(ValueError, "Captured finding viewport facts disagree"):
                    build_agent_bundle(stale.finding_dir, fixture["runtime_cmd"])


if __name__ == "__main__":
    unittest.main()
