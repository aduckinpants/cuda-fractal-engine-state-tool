from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from cuda_fractal_state_tool.user_workflow import (
    CAPABILITY_PROFILE,
    SessionState,
    UserWorkflowSession,
    build_finding_intake_packet,
    load_finding_context,
)


class UserWorkflowTests(unittest.TestCase):
    def _capture(self, root: Path) -> Path:
        capture = root / "capture"
        capture.mkdir()
        (capture / "state.json").write_text(
            json.dumps(
                {
                    "state_version": 3,
                    "fractal_type": "explaino_all",
                    "view": {"auto_max_iter": False},
                    "params": {
                        "max_iter": 500,
                        "multibrot_power": 3,
                        "julia_c_real": -0.7,
                        "color_signal": "root_index",
                        "color_shape": "identity",
                        "color_palette": "joy",
                        "color_grading": "basin_default",
                    },
                    "render": {"width": 80, "height": 60, "device_id": 0},
                }
            ),
            encoding="utf-8",
        )
        (capture / "fractal-state.json").write_text(
            json.dumps(
                {
                    "schema_id": "viewer.finding_fractal_state.v1",
                    "capture_context": {"fractal_type": "explaino_all"},
                    "active_fractal_controls": {
                        "max_iter": 500,
                        "explaino_seed": 38,
                        "explaino_mix": 0.5,
                    },
                    "derived_runtime_values": {"last_iters_avg": 8},
                    "color_pipeline": {
                        "color_signal": "root_index",
                        "color_shape": "identity",
                        "color_palette": "joy",
                        "color_grading": "basin_default",
                    },
                    "omitted_groups": ["inactive_family_parameter_groups"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        Image.new("RGB", (80, 60), (10, 20, 30)).save(capture / "frame.png")
        return capture

    def _runtime(self, root: Path) -> Path:
        runtime = root / "runtime"
        contract_dir = runtime / "ui_salt" / "generated"
        contract_dir.mkdir(parents=True)
        ui_dir = runtime / "ui"
        ui_dir.mkdir()
        cmd = runtime / "fractal_ui.cmd"
        cmd.write_text(
            '@echo off\nif /I "%1"=="--describe-parameter-surface-json" copy /y "%~dp0parameter-surface.fixture.json" "%~2" >nul\n',
            encoding="utf-8",
        )
        (runtime / "fractal_ui_active.txt").write_text("fractal_ui.exe\n", encoding="utf-8")
        (runtime / "fractal_ui.exe").write_bytes(b"engine")
        (runtime / "parameter-surface.fixture.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "lanes": [
                        {
                            "fractal_id": "explaino_all",
                            "controls": [
                                {
                                    "control_id": "explaino_seed",
                                    "owner_lane": "explaino_all",
                                    "binding_path": "fractal.params.explaino_seed",
                                    "control_type": "slider_double",
                                    "value_type": "double",
                                    "default_value": "0",
                                    "candidate_value": "0.001",
                                    "runtime_binding_kind": "double",
                                    "binding_resolves": True,
                                    "state_io_key": "explaino_seed",
                                    "has_validation_range": True,
                                    "animatable": True,
                                    "visibility_surface_id": "default",
                                    "default_visible": True,
                                }
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (ui_dir / "fractal_binding_surface_v1.ui_schema.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "namespace": "fractal",
                    "panels": [
                        {
                            "id": "fractal",
                            "label": "Fractal",
                            "controls": [
                                {
                                    "id": "explaino_seed",
                                    "type": "slider_double",
                                    "label": "Explaino Seed",
                                    "help": "Primary Explaino seed control.",
                                    "value_type": "double",
                                    "ui_min": -10.0,
                                    "ui_max": 10.0,
                                    "step": 0.001,
                                    "default": 0.0,
                                    "binding": {"kind": "param", "path": "fractal.params.explaino_seed"},
                                    "visible_if": {
                                        "op": "in",
                                        "path": "fractal.view.fractal_type",
                                        "value": "explaino,explaino_all",
                                    },
                                }
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (contract_dir / "color_pipeline_function_library.contract.v1.json").write_text(
            json.dumps(
                {
                    "function_library": {
                        "lanes": [
                            {
                                "id": "source",
                                "label": "Source",
                                "default": "root_index",
                                "functions": [
                                    {"id": "root_index", "label": "Root Index", "description": "Use the resolved root classification."}
                                ],
                            },
                            {
                                "id": "shape",
                                "label": "Shape",
                                "default": "identity",
                                "functions": [
                                    {"id": "identity", "label": "Identity", "description": "Keep the source signal unchanged."},
                                    {"id": "repeat", "label": "Repeat", "description": "Tile the signal into repeating bands."},
                                ],
                            },
                            {
                                "id": "palette",
                                "label": "Palette",
                                "default": "joy_root_palette",
                                "functions": [
                                    {"id": "joy_root_palette", "label": "Joy Root", "description": "Use the joy-basins palette lineage."}
                                ],
                            },
                            {
                                "id": "grading",
                                "label": "Grading",
                                "default": "basin_default",
                                "functions": [
                                    {"id": "basin_default", "label": "Basin Default", "description": "Preserve basin grading defaults."}
                                ],
                            },
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        return cmd

    def test_real_import_summary_and_exact_packet_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            capture = self._capture(root)
            finding = load_finding_context(capture, root / "workspace")
            packet = build_finding_intake_packet(finding, self._runtime(root))
            self.assertIn(finding.finding_id, finding.summary_text)
            self.assertEqual(packet.capability_profile, CAPABILITY_PROFILE)
            self.assertEqual(hashlib.sha256(packet.packet_text.encode("utf-8")).hexdigest(), packet.packet_sha256)
            self.assertEqual(packet.packet_path.read_bytes().decode("utf-8"), packet.packet_text)
            manifest = json.loads(packet.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["packet_sha256"], packet.packet_sha256)
            self.assertEqual(manifest["finding_id"], finding.finding_id)
            self.assertEqual(manifest["review_fractal_state_sha256"], finding.review_fractal_state_sha256)
            self.assertEqual(manifest["parameter_surface_sha256"], packet.parameter_surface_sha256)
            parameter_surface_path = packet.manifest_path.parent / manifest["parameter_surface_path"]
            self.assertEqual(hashlib.sha256(parameter_surface_path.read_bytes()).hexdigest(), packet.parameter_surface_sha256)
            self.assertIn("# CUDA Fractal Finding — Agent Exploration Packet", packet.packet_text)
            self.assertIn("Begin with a curiosity-driven discussion", packet.packet_text)
            self.assertIn("Surface anything mathematically", packet.packet_text)
            self.assertIn("clearly separating serialized facts, visual observations", packet.packet_text)
            self.assertIn("Do not invent mathematical claims", packet.packet_text)
            self.assertIn("is optional until the user wants to try a concrete change", packet.packet_text)
            self.assertIn("A field's presence in `state.json` does not prove", packet.packet_text)
            self.assertIn("engine-generated applicable-parameter projection", packet.packet_text)
            self.assertIn("Applicability is still not counterfactual sensitivity proof", packet.packet_text)
            projection_marker = "## Engine-generated applicable fractal parameters"
            projection_start = packet.packet_text.index("```json", packet.packet_text.index(projection_marker)) + len("```json")
            projection_end = packet.packet_text.index("```", projection_start)
            projection = json.loads(packet.packet_text[projection_start:projection_end])
            self.assertEqual(projection["fractal_id"], "explaino_all")
            self.assertEqual([item["control_id"] for item in projection["controls"]], ["explaino_seed"])
            seed = projection["controls"][0]
            self.assertEqual(seed["current_value"], 38)
            self.assertEqual(seed["current_value_source"], "fractal-state.json.active_fractal_controls")
            self.assertEqual(seed["schema_properties"]["label"], "Explaino Seed")
            self.assertEqual(seed["schema_properties"]["ui_min"], -10.0)
            self.assertNotIn("multibrot_power", {item["control_id"] for item in projection["controls"]})
            self.assertNotIn("julia_c_real", {item["control_id"] for item in projection["controls"]})
            self.assertIn("viewer.finding_fractal_state.v1", packet.packet_text)
            self.assertIn('"active_fractal_controls": {', packet.packet_text)
            self.assertIn('"fractal_type": "explaino_all"', packet.packet_text)
            self.assertIn("`repeat` (Repeat): Tile the signal into repeating bands.", packet.packet_text)
            self.assertIn('"color_pipeline_draft": {', packet.packet_text)
            self.assertIn("These examples were generated and accepted", packet.packet_text)
            self.assertNotIn("Return one proposal_v1 JSON object only", packet.packet_text)
            self.assertNotIn(str(capture), packet.packet_text)
            self.assertNotIn(str(root / "workspace"), packet.packet_text)

    def test_session_transitions_packet_change_and_reset_invalidate_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding = load_finding_context(self._capture(root), root / "workspace")
            runtime = self._runtime(root)
            packet_one = build_finding_intake_packet(finding, runtime)
            packet_two = build_finding_intake_packet(finding, runtime)
            session = UserWorkflowSession()
            generation = session.begin_finding_change()
            session.accept_finding(finding)
            self.assertEqual(session.state, SessionState.FINDING_READY)
            session.accept_packet(packet_one)
            self.assertEqual(session.state, SessionState.PACKET_READY)
            session.set_proposal_text('{"proposal_version":1}')
            self.assertEqual(session.state, SessionState.PROPOSAL_DIRTY)
            session.begin_proof()
            self.assertEqual(session.state, SessionState.PROVING)
            session.accept_proof_result(SimpleNamespace(status="proven"))
            self.assertEqual(session.state, SessionState.PROVEN)
            session.set_proposal_text('{"proposal_version":1}\n')
            self.assertEqual(session.state, SessionState.PROPOSAL_DIRTY)
            self.assertIsNone(session.proof_result)
            session.accept_packet(packet_two)
            self.assertEqual(session.state, SessionState.PROPOSAL_DIRTY)
            self.assertNotEqual(packet_one.packet_id, packet_two.packet_id)
            session.reset()
            self.assertEqual(session.state, SessionState.EMPTY)
            self.assertGreater(session.generation, generation)
            self.assertIsNone(session.packet)
            self.assertEqual(session.proposal_text, "")


if __name__ == "__main__":
    unittest.main()
