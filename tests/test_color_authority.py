from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from cuda_fractal_state_tool.color_authority import run_controlled_color_authority_proof
from cuda_fractal_state_tool.process_utils import ProcessResult


class ColorAuthorityProofTests(unittest.TestCase):
    def _runtime_fixture(self, root: Path) -> tuple[Path, Path]:
        runtime = root / "runtime"
        contract_dir = runtime / "ui_salt" / "generated"
        contract_dir.mkdir(parents=True)
        runtime_cmd = runtime / "fractal_ui.cmd"
        runtime_cmd.write_text("@echo off\n", encoding="utf-8")
        (runtime / "fractal_ui_active.txt").write_text("fractal_ui.exe\n", encoding="utf-8")
        (runtime / "fractal_ui.exe").write_bytes(b"engine")
        contract = {
            "function_library": {
                "lanes": [
                    {"id": "source", "default": "root_index", "functions": [{"id": "root_index"}]},
                    {
                        "id": "shape",
                        "default": "identity",
                        "functions": [{"id": "identity"}, {"id": "repeat"}, {"id": "posterize"}],
                    },
                    {"id": "palette", "default": "joy_root_palette", "functions": [{"id": "joy_root_palette"}]},
                    {"id": "grading", "default": "basin_default", "functions": [{"id": "basin_default"}]},
                ]
            }
        }
        (contract_dir / "color_pipeline_function_library.contract.v1.json").write_text(
            json.dumps(contract), encoding="utf-8"
        )
        base_state = root / "base.json"
        base_state.write_text(
            json.dumps(
                {
                    "state_version": 3,
                    "fractal_type": "explaino_all",
                    "view": {"auto_max_iter": False},
                    "params": {"color_shape": "identity", "max_iter": 500},
                    "render": {"width": 2, "height": 2, "device_id": 0},
                }
            ),
            encoding="utf-8",
        )
        return runtime_cmd, base_state

    def _fake_runtime(self, inert_repeat: bool = False):
        def fake_run(command, cwd, timeout_seconds=None, env=None):
            if "--validate-ui-salt-contract" in command:
                report_path = Path(command[command.index("--ui-salt-contract-report-json") + 1])
                self.assertTrue(report_path.parent.exists())
                report_path.write_text('{"ok":true}', encoding="utf-8")
            elif "--capture-diagnostic" in command:
                input_path = Path(command[command.index("--load-state-json") + 1])
                output_dir = Path(command[command.index("--diagnostics-out-dir") + 1])
                output_dir.mkdir(parents=True, exist_ok=True)
                state = json.loads(input_path.read_text(encoding="utf-8"))
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
                state.setdefault("params", {})["color_shape"] = shape
                state["color_pipeline_draft"] = {
                    "next_row_id": 5,
                    "lanes": [
                        {"lane_id": "source", "rows": [{"ui_row_id": 1, "function_id": "root_index", "enabled": True, "params": {}}]},
                        {"lane_id": "shape", "rows": [{"ui_row_id": 2, "function_id": shape, "enabled": True, "params": {}}]},
                        {"lane_id": "palette", "rows": [{"ui_row_id": 3, "function_id": "joy_root_palette", "enabled": True, "params": {}}]},
                        {"lane_id": "grading", "rows": [{"ui_row_id": 4, "function_id": "basin_default", "enabled": True, "params": {}}]},
                    ],
                }
                (output_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
                visible_shape = "identity" if inert_repeat and shape == "repeat" else shape
                color = (255, 255, 255) if visible_shape in {"repeat", "posterize"} else (0, 0, 0)
                Image.new("RGB", (2, 2), color).save(output_dir / "frame.bmp")
            return ProcessResult(
                command=list(command),
                cwd=str(cwd),
                pid=7,
                exit_code=0,
                timed_out=False,
                elapsed_seconds=0.01,
                stdout="ok",
                stderr="",
                observed_process_tree=[],
            )

        return fake_run

    def test_controlled_proof_uses_engine_action_and_replays_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_cmd, base_state = self._runtime_fixture(root)
            with patch("cuda_fractal_state_tool.color_authority.run_command", side_effect=self._fake_runtime()):
                result = run_controlled_color_authority_proof(runtime_cmd, base_state, root / "proof")
            self.assertEqual(result.status, "passed")
            self.assertEqual((result.selected_lane_id, result.selected_function_id), ("shape", "repeat"))
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["replay"]["parity_classification"], "exact_encoded_frame_match")
            self.assertTrue(receipt["replay"]["selection_survived"])
            self.assertNotEqual(
                receipt["controlled_base"]["parity"]["left"]["decoded_rgba_sha256"],
                receipt["selected_change"]["rendered_effect"]["right"]["decoded_rgba_sha256"],
            )

    def test_inert_preferred_pair_is_recorded_and_next_grounded_function_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_cmd, base_state = self._runtime_fixture(root)
            with patch(
                "cuda_fractal_state_tool.color_authority.run_command",
                side_effect=self._fake_runtime(inert_repeat=True),
            ):
                result = run_controlled_color_authority_proof(runtime_cmd, base_state, root / "proof")
            self.assertEqual(result.selected_function_id, "posterize")
            attempts = json.loads((result.output_root / "attempts.json").read_text(encoding="utf-8"))
            self.assertEqual(attempts[0]["status"], "visually_inert")
            self.assertEqual(attempts[1]["status"], "visible_effect")


if __name__ == "__main__":
    unittest.main()
