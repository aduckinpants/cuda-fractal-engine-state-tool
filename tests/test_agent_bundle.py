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
        contract = {
            "schema_version": 1,
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
            self.assertIn("params.exposure", by_path)
            self.assertIn("view.center_x", by_path)
            self.assertEqual(by_path["view.center_x"]["companion_paths"], ["view.center_hp_x"])
            self.assertNotIn("params.color_glow", by_path)
            self.assertFalse(any(entry["source_control_id"] == "live_root_pattern" for entry in surface["entries"]))
            self.assertFalse(any(entry["source_control_id"] == "hidden_control" for entry in surface["entries"]))
            self.assertEqual(
                surface["authority_refs"]["parameter_surface_sha256"],
                hashlib.sha256(fixture["surface_bytes"]).hexdigest(),
            )

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

    def test_build_bundle_preserves_exact_artifacts_and_publishes_coherent_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = self._fixture(root)
            imported = SourceCaptureImporter(root / "workspace").import_capture(fixture["capture"])
            exports = [
                fixture["surface_bytes"],
                fixture["catalog_bytes"],
                fixture["surface_bytes"],
                fixture["catalog_bytes"],
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
            self.assertIn("Copying this Markdown does not transport those files", packet)
            self.assertNotIn("proposal_v1", packet)
            self.assertNotIn("capability_profile", packet)
            self.assertNotIn("select_function", packet)
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
                        fixture["surface_bytes"],
                        fixture["catalog_bytes"],
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
                fixture["surface_bytes"],
                fixture["catalog_bytes"],
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
                        fixture["surface_bytes"],
                        fixture["catalog_bytes"],
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
                        fixture["surface_bytes"],
                        fixture["catalog_bytes"],
                    ],
                ),
            ):
                bundle = build_agent_bundle(imported.finding_dir, fixture["runtime_cmd"])
            (bundle.packet_dir / "state.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed after publication"):
                load_agent_bundle_handoff(bundle.packet_dir)


if __name__ == "__main__":
    unittest.main()
