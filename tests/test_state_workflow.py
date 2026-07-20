from __future__ import annotations

import ntpath
import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.baseline import freeze_phase0_baseline
from cuda_fractal_state_tool.intake import build_intake_packet
from cuda_fractal_state_tool.json_utils import dumps_pretty
from cuda_fractal_state_tool.proposal import build_color_grading_example, build_color_shape_example, build_max_iter_example, build_noop_example
from cuda_fractal_state_tool.runtime_surface import build_detached_viewer_launch_command, build_replay_command
from cuda_fractal_state_tool.state_workflow import execute_proposal_workflow


RUNTIME_CMD = Path(r"D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd")
PROBE_ROOT = Path(".local") / "runtime_probe"


@unittest.skipUnless(RUNTIME_CMD.exists() and (PROBE_ROOT / "capture_one" / "state.json").exists(), "Published runtime and Phase 0 probe artifacts are required")
class StateWorkflowIntegrationTests(unittest.TestCase):
    def test_replay_command_construction_uses_absolute_paths(self) -> None:
        command = build_replay_command(RUNTIME_CMD, Path("x.json"), Path("out"))
        self.assertEqual(command[0:4], ["cmd.exe", "/d", "/c", str(RUNTIME_CMD)])
        self.assertTrue(ntpath.isabs(command[5]))
        self.assertTrue(ntpath.isabs(command[8]))

    def test_detached_viewer_command_construction(self) -> None:
        command = build_detached_viewer_launch_command(RUNTIME_CMD, Path("candidate.json").resolve())
        self.assertEqual(command[0:4], ["cmd.exe", "/d", "/c", str(RUNTIME_CMD)])
        self.assertEqual(command[4], "--load-state-json")

    def test_phase1_noop_and_override_workflows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            frozen = freeze_phase0_baseline(PROBE_ROOT, root / "baselines")

            noop = execute_proposal_workflow(
                build_noop_example(frozen.manifest["state_sha256"]),
                frozen.manifest_path,
                root / "working_states",
                "noop",
                runtime_cmd_path=RUNTIME_CMD,
            )
            self.assertEqual(noop.status, "runtime_proof_succeeded")
            self.assertEqual(noop.transport_candidate_path.read_bytes(), frozen.state_path.read_bytes())
            self.assertIsNotNone(noop.proven_state_path)
            self.assertTrue((noop.working_state_dir / "candidate_replay_diff.json").exists())
            self.assertTrue(noop.validation_run_manifest_path.exists())
            self.assertTrue(noop.validation_run_dir.exists())
            self.assertEqual(noop.runtime_status, "runtime_success")

            max_iter = execute_proposal_workflow(
                build_max_iter_example(frozen.manifest["state_sha256"]),
                frozen.manifest_path,
                root / "working_states",
                "max_iter",
                runtime_cmd_path=RUNTIME_CMD,
            )
            self.assertEqual(max_iter.status, "runtime_proof_succeeded")
            self.assertIn('"max_iter": 700', max_iter.transport_candidate_path.read_text(encoding="utf-8"))

            color = execute_proposal_workflow(
                build_color_shape_example(frozen.manifest["state_sha256"]),
                frozen.manifest_path,
                root / "working_states",
                "color_shape",
                runtime_cmd_path=RUNTIME_CMD,
            )
            self.assertEqual(color.status, "runtime_proof_succeeded")
            replay_text = color.replay_state_path.read_text(encoding="utf-8") if color.replay_state_path else ""
            self.assertIn('"function_id": "repeat"', replay_text)
            self.assertTrue((color.working_state_dir / "stdout.txt").exists())
            self.assertTrue((color.working_state_dir / "stderr.txt").exists())
            self.assertTrue((color.working_state_dir / "validation.json").exists())
            self.assertTrue((color.validation_run_manifest_path).exists())
            self.assertEqual(color.runtime_status, "runtime_success")

            grading = execute_proposal_workflow(
                build_color_grading_example(frozen.manifest["state_sha256"]),
                frozen.manifest_path,
                root / "working_states",
                "color_grading",
                runtime_cmd_path=RUNTIME_CMD,
            )
            self.assertEqual(grading.status, "runtime_proof_succeeded")
            grading_text = grading.replay_state_path.read_text(encoding="utf-8") if grading.replay_state_path else ""
            self.assertIn('"function_id": "basin_default"', grading_text)
            self.assertEqual(grading.runtime_status, "runtime_success")

            packet = build_intake_packet(frozen.manifest_path, PROBE_ROOT / "replay_one" / "state.json")
            self.assertIn("Return a sparse proposal_v1 JSON document", packet)
            self.assertIn("params.max_iter", packet)
            self.assertIn("params.color_shape", packet)
            self.assertIn("params.color_grading", packet)
            self.assertIn("schema provenance status: mismatched", packet)


if __name__ == "__main__":
    unittest.main()