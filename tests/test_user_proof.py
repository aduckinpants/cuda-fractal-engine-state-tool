from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from cuda_fractal_state_tool.process_utils import ProcessResult
from cuda_fractal_state_tool.user_proof import execute_bound_proof, validate_launch_readiness
from cuda_fractal_state_tool.user_workflow import build_finding_intake_packet, load_finding_context


class FakeJob:
    def __init__(self, lose_selection_on_replay: bool = False) -> None:
        self.commands: list[list[str]] = []
        self.lose_selection_on_replay = lose_selection_on_replay

    def run_process(self, command, cwd, timeout_seconds=None, env=None):
        command = list(command)
        self.commands.append(command)
        state_path = Path(command[command.index("--load-state-json") + 1])
        output_dir = Path(command[command.index("--diagnostics-out-dir") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        shape = state.get("params", {}).get("color_shape", "identity")
        actions = [
            command[index + 1]
            for index, value in enumerate(command)
            if value == "--color-pipeline-action"
        ]
        for action in actions:
            parts = action.split(":")
            if parts[:3] == ["select_function", "shape", "0"]:
                shape = parts[3]
        if self.lose_selection_on_replay and len(self.commands) == 2:
            shape = "identity"
        state.setdefault("params", {})["color_shape"] = shape
        state["color_pipeline_draft"] = {
            "next_row_id": 5,
            "lanes": [
                {"lane_id": "source", "rows": [{"ui_row_id": 1, "function_id": "root_index", "enabled": True, "parameter_values": []}]},
                {"lane_id": "shape", "rows": [{"ui_row_id": 2, "function_id": shape, "enabled": True, "parameter_values": []}]},
                {"lane_id": "palette", "rows": [{"ui_row_id": 3, "function_id": "joy_root_palette", "enabled": True, "parameter_values": []}]},
                {"lane_id": "grading", "rows": [{"ui_row_id": 4, "function_id": "basin_default", "enabled": True, "parameter_values": []}]},
            ],
        }
        (output_dir / "state.json").write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
        Image.new("RGB", (4, 3), (120, 40, 20) if shape == "repeat" else (10, 20, 30)).save(
            output_dir / "frame.bmp"
        )
        return ProcessResult(
            command=command,
            cwd=str(cwd),
            pid=12,
            exit_code=0,
            timed_out=False,
            elapsed_seconds=0.01,
            stdout="ok",
            stderr="",
            observed_process_tree=[],
        )


class UserProofTests(unittest.TestCase):
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
                        "color_signal": "root_index",
                        "color_shape": "identity",
                        "color_palette": "joy",
                        "color_grading": "basin_default",
                    },
                    "render": {"width": 4, "height": 3, "device_id": 0},
                }
            ),
            encoding="utf-8",
        )
        Image.new("RGB", (4, 3), (10, 20, 30)).save(capture / "frame.png")
        return capture

    def _runtime(self, root: Path) -> Path:
        runtime = root / "runtime"
        contract_dir = runtime / "ui_salt" / "generated"
        contract_dir.mkdir(parents=True)
        ui_dir = runtime / "ui"
        ui_dir.mkdir()
        cmd = runtime / "fractal_ui.cmd"
        cmd.write_text(
            "@echo off\n"
            'if /I "%1"=="--describe-parameter-surface-json" copy /y "%~dp0parameter-surface.fixture.json" "%~2" >nul\n'
            'if /I "%1"=="--describe-fractal-catalog-json" copy /y "%~dp0fractal-catalog.fixture.json" "%~2" >nul\n',
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
        (runtime / "fractal-catalog.fixture.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "entries": [
                        {
                            "selector_id": "explaino_all",
                            "display_name": "Explaino All",
                            "category": "explaino",
                            "family": "explaino",
                            "formula_growth_surface": "native_composite_formula",
                            "capability_flags": ["root_basin_coloring"],
                            "runtime_flags": ["basin_coloring"],
                            "description_status": "reviewed",
                            "description": {
                                "math_summary": "Reviewed summary.",
                                "recurrence_or_field_model": "Reviewed recurrence.",
                                "state_order": "Reviewed state order.",
                                "termination_or_classification": "Reviewed termination.",
                                "interpretation_notes": "Reviewed interpretation boundary.",
                                "source_refs": ["ui_app/src/example.cpp#Example"],
                            },
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
        lanes = []
        for lane_id, label, default, functions in (
            ("source", "Source", "root_index", [("root_index", "Root Index", "Use root classification.")]),
            ("shape", "Shape", "identity", [("identity", "Identity", "Keep the signal."), ("repeat", "Repeat", "Repeat the signal.")]),
            ("palette", "Palette", "joy_root_palette", [("joy_root_palette", "Joy", "Use joy colors.")]),
            ("grading", "Grading", "basin_default", [("basin_default", "Basin", "Use basin grading.")]),
        ):
            lanes.append(
                {
                    "id": lane_id,
                    "label": label,
                    "default": default,
                    "functions": [
                        {"id": function_id, "label": function_label, "description": description}
                        for function_id, function_label, description in functions
                    ],
                }
            )
        (contract_dir / "color_pipeline_function_library.contract.v1.json").write_text(
            json.dumps({"function_library": {"lanes": lanes}}), encoding="utf-8"
        )
        return cmd

    def test_bound_lane_proposal_materializes_replays_and_becomes_launch_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding = load_finding_context(self._capture(root), root / "workspace")
            runtime = self._runtime(root)
            packet = build_finding_intake_packet(finding, runtime)
            proposal = json.dumps(
                {
                    "proposal_version": 1,
                    "base_state": {
                        "finding_id": finding.finding_id,
                        "sha256": finding.authoring_base_sha256,
                    },
                    "overrides": {
                        "color_pipeline_draft": {
                            "lanes": [{"lane_id": "shape", "function_id": "repeat"}]
                        }
                    },
                },
                indent=2,
            )
            job = FakeJob()
            result = execute_bound_proof(finding, packet, proposal, runtime, job)
            self.assertEqual(result.status, "proven")
            self.assertEqual(result.receipt_path.parent.parent.name, "proofs")
            self.assertNotIn(result.proposal_text_sha256, result.receipt_path.parts)
            self.assertEqual(len(job.commands), 2)
            self.assertIn("select_function:shape:0:repeat", job.commands[0])
            self.assertNotIn("--color-pipeline-action", job.commands[1])
            self.assertEqual(validate_launch_readiness(result, packet, proposal, runtime), [])
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["binding"]["packet_id"], packet.packet_id)
            self.assertEqual(receipt["requested_selections"], {"shape": "repeat"})
            self.assertTrue(receipt["replay"]["frame_comparison"]["decoded_equal"])
            self.assertTrue(receipt["replay"]["requested_selection_survived"])
            self.assertTrue(receipt["proven_candidate"]["launch_ready"])
            self.assertIn("--load-state-json", receipt["proven_candidate"]["launch_command"])

    def test_rejected_proposal_gets_exact_bound_repair_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding = load_finding_context(self._capture(root), root / "workspace")
            runtime = self._runtime(root)
            packet = build_finding_intake_packet(finding, runtime)
            proposal = '{"proposal_version":1,"base_state":{"finding_id":"wrong","sha256":"wrong"},"overrides":{}}'
            job = FakeJob()
            result = execute_bound_proof(finding, packet, proposal, runtime, job)
            self.assertEqual(result.status, "rejected")
            self.assertEqual(job.commands, [])
            self.assertIn(packet.packet_id, result.repair_packet_text or "")
            self.assertIn(result.proposal_text_sha256, result.repair_packet_text or "")
            self.assertIn("does not match", result.message)

    def test_action_free_replay_must_preserve_requested_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding = load_finding_context(self._capture(root), root / "workspace")
            runtime = self._runtime(root)
            packet = build_finding_intake_packet(finding, runtime)
            proposal = json.dumps(
                {
                    "proposal_version": 1,
                    "base_state": {"finding_id": finding.finding_id, "sha256": finding.authoring_base_sha256},
                    "overrides": {
                        "color_pipeline_draft": {
                            "lanes": [{"lane_id": "shape", "function_id": "repeat"}]
                        }
                    },
                }
            )
            result = execute_bound_proof(
                finding,
                packet,
                proposal,
                runtime,
                FakeJob(lose_selection_on_replay=True),
            )
            self.assertEqual(result.status, "rejected")
            self.assertIn("Action-free replay lost selection", result.message)
            self.assertIsNone(result.repair_packet_text)

    def test_candidate_tampering_invalidates_launch_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding = load_finding_context(self._capture(root), root / "workspace")
            runtime = self._runtime(root)
            packet = build_finding_intake_packet(finding, runtime)
            proposal = json.dumps(
                {
                    "proposal_version": 1,
                    "base_state": {"finding_id": finding.finding_id, "sha256": finding.authoring_base_sha256},
                    "overrides": {"params.max_iter": 600},
                }
            )
            result = execute_bound_proof(finding, packet, proposal, runtime, FakeJob())
            assert result.candidate_path is not None
            self.assertIn("Proposal text changed after proof", validate_launch_readiness(result, packet, proposal + "\n", runtime))
            result.candidate_path.write_text("{}", encoding="utf-8")
            self.assertIn("Proven candidate changed after proof", validate_launch_readiness(result, packet, proposal, runtime))

    def test_runtime_change_rejects_old_packet_without_agent_repair(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding = load_finding_context(self._capture(root), root / "workspace")
            runtime = self._runtime(root)
            packet = build_finding_intake_packet(finding, runtime)
            (runtime.parent / "fractal_ui.exe").write_bytes(b"changed-engine")
            proposal = json.dumps(
                {
                    "proposal_version": 1,
                    "base_state": {"finding_id": finding.finding_id, "sha256": finding.authoring_base_sha256},
                    "overrides": {"params.max_iter": 600},
                }
            )
            job = FakeJob()
            result = execute_bound_proof(finding, packet, proposal, runtime, job)
            self.assertEqual(result.status, "rejected")
            self.assertEqual(job.commands, [])
            self.assertIsNone(result.repair_packet_text)
            self.assertIn("Runtime identity changed", result.message)

    def test_contract_change_rejects_old_packet_without_agent_repair(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding = load_finding_context(self._capture(root), root / "workspace")
            runtime = self._runtime(root)
            packet = build_finding_intake_packet(finding, runtime)
            contract = runtime.parent / "ui_salt" / "generated" / "color_pipeline_function_library.contract.v1.json"
            contract.write_text(contract.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            proposal = json.dumps(
                {
                    "proposal_version": 1,
                    "base_state": {"finding_id": finding.finding_id, "sha256": finding.authoring_base_sha256},
                    "overrides": {"params.max_iter": 600},
                }
            )
            result = execute_bound_proof(finding, packet, proposal, runtime, FakeJob())
            self.assertEqual(result.status, "rejected")
            self.assertIsNone(result.repair_packet_text)
            self.assertIn("UI-Salt contract changed", result.message)

    def test_persisted_packet_tampering_invalidates_launch_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding = load_finding_context(self._capture(root), root / "workspace")
            runtime = self._runtime(root)
            packet = build_finding_intake_packet(finding, runtime)
            proposal = json.dumps(
                {
                    "proposal_version": 1,
                    "base_state": {"finding_id": finding.finding_id, "sha256": finding.authoring_base_sha256},
                    "overrides": {"params.max_iter": 600},
                }
            )
            result = execute_bound_proof(finding, packet, proposal, runtime, FakeJob())
            packet.packet_path.write_text("changed", encoding="utf-8")
            self.assertIn(
                "Persisted packet payload changed after proof",
                validate_launch_readiness(result, packet, proposal, runtime),
            )

    def test_distinct_packet_cannot_inherit_existing_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding = load_finding_context(self._capture(root), root / "workspace")
            runtime = self._runtime(root)
            original_packet = build_finding_intake_packet(finding, runtime)
            proposal = json.dumps(
                {
                    "proposal_version": 1,
                    "base_state": {"finding_id": finding.finding_id, "sha256": finding.authoring_base_sha256},
                    "overrides": {"params.max_iter": 600},
                }
            )
            result = execute_bound_proof(finding, original_packet, proposal, runtime, FakeJob())
            replacement_packet = build_finding_intake_packet(finding, runtime)
            errors = validate_launch_readiness(result, replacement_packet, proposal, runtime)
            self.assertIn("Packet ID changed after proof", errors)
            self.assertIn("Packet payload binding changed after proof", errors)

    def test_parameter_surface_evidence_tampering_rejects_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding = load_finding_context(self._capture(root), root / "workspace")
            runtime = self._runtime(root)
            packet = build_finding_intake_packet(finding, runtime)
            (packet.manifest_path.parent / "parameter-surface.json").write_text("{}", encoding="utf-8")
            proposal = json.dumps(
                {
                    "proposal_version": 1,
                    "base_state": {"finding_id": finding.finding_id, "sha256": finding.authoring_base_sha256},
                    "overrides": {"params.max_iter": 600},
                }
            )
            job = FakeJob()
            result = execute_bound_proof(finding, packet, proposal, runtime, job)
            self.assertEqual(result.status, "rejected")
            self.assertEqual(job.commands, [])
            self.assertIsNone(result.repair_packet_text)
            self.assertIn("parameter-surface descriptor changed", result.message)


if __name__ == "__main__":
    unittest.main()
