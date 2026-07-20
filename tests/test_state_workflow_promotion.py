from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.json_utils import dumps_pretty
from cuda_fractal_state_tool.proposal import build_noop_example
from cuda_fractal_state_tool.runtime_surface import sha256_file
from cuda_fractal_state_tool.state_workflow import execute_proposal_workflow
from cuda_fractal_state_tool.process_utils import ProcessResult


class StateWorkflowPromotionTests(unittest.TestCase):
    def _make_baseline(self, root: Path) -> Path:
        baseline_dir = root / "baselines" / "runtime-default-v1"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        state_path = baseline_dir / "state.json"
        state_path.write_text(
            '{"state_version": 3, "fractal_type": "explaino_all", "view": {}, "params": {"max_iter": 500, "color_shape": "identity", "color_signal": "root_index", "color_palette": "joy", "color_grading": "basin_default"}, "render": {}}\n',
            encoding="utf-8",
        )
        manifest_path = baseline_dir / "manifest.json"
        manifest_path.write_text(
            dumps_pretty(
                {
                    "baseline_id": "runtime-default-v1",
                    "state_sha256": sha256_file(state_path),
                    "runtime_identity": {"launcher_sha256": "abc"},
                    "replay_proven": True,
                }
            ),
            encoding="utf-8",
        )
        return manifest_path

    def test_promotion_profile_emits_promoted_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = self._make_baseline(root)
            working_root = root / "working_states"
            runtime_cmd = root / "runtime" / "fractal_ui.cmd"
            runtime_cmd.parent.mkdir(parents=True, exist_ok=True)
            runtime_cmd.write_text("@echo off\n", encoding="utf-8")

            def fake_replay(runtime_cmd_path: Path, candidate_path: Path, replay_dir: Path, timeout_seconds: float = 90.0) -> ProcessResult:
                replay_dir.mkdir(parents=True, exist_ok=True)
                replay_doc = (
                    candidate_path.read_text(encoding="utf-8")[:-2]
                    + ', "color_pipeline_draft": {"lanes": [{"lane_id": "shape", "function_id": "repeat"}]}, "sidecar_orientation": {"yaw": 0.1}}\n'
                )
                (replay_dir / "state.json").write_text(replay_doc, encoding="utf-8")
                (replay_dir / "frame.bmp").write_text("bmp", encoding="utf-8")
                return ProcessResult(
                    command=["cmd.exe"],
                    cwd=str(runtime_cmd_path.parent),
                    pid=123,
                    exit_code=0,
                    timed_out=False,
                    elapsed_seconds=0.1,
                    stdout="ok",
                    stderr="",
                    observed_process_tree=[],
                )

            with patch("cuda_fractal_state_tool.state_workflow.replay_transport_candidate", side_effect=fake_replay), patch(
                "cuda_fractal_state_tool.state_workflow.build_runtime_identity",
                return_value={"launcher_sha256": "abc"},
            ):
                baseline_sha = sha256_file(manifest_path.with_name("state.json"))
                result = execute_proposal_workflow(
                    build_noop_example(baseline_sha),
                    manifest_path,
                    working_root,
                    "promoted_run",
                    runtime_cmd_path=runtime_cmd,
                    promotion_profile="observed_runtime_enrichment_v1",
                )

            self.assertEqual(result.status, "runtime_proof_succeeded")
            self.assertEqual(result.runtime_status, "runtime_success")
            self.assertEqual(result.promotion_profile, "observed_runtime_enrichment_v1")
            self.assertIsNotNone(result.promoted_state_path)
            self.assertIsNotNone(result.promotion_report_path)
            promoted_text = result.promoted_state_path.read_text(encoding="utf-8")
            report_text = result.promotion_report_path.read_text(encoding="utf-8")
            self.assertIn('"color_pipeline_draft"', promoted_text)
            self.assertIn('"sidecar_orientation"', promoted_text)
            self.assertIn('"applied_keys"', report_text)
            self.assertIn('"color_pipeline_draft"', report_text)
            self.assertIn('"allowed_classifications"', report_text)
            self.assertIn('"runtime_replay_artifact_enrichment"', report_text)
            self.assertIn('"derived_runtime_state"', report_text)
            self.assertIn('"blocked_keys": {}', report_text)

    def test_unknown_promotion_profile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = self._make_baseline(root)
            runtime_cmd = root / "runtime" / "fractal_ui.cmd"
            runtime_cmd.parent.mkdir(parents=True, exist_ok=True)
            runtime_cmd.write_text("@echo off\n", encoding="utf-8")
            baseline_sha = sha256_file(manifest_path.with_name("state.json"))
            with self.assertRaises(ValueError):
                execute_proposal_workflow(
                    build_noop_example(baseline_sha),
                    manifest_path,
                    root / "working_states",
                    "bad_profile",
                    runtime_cmd_path=runtime_cmd,
                    promotion_profile="not_a_profile",
                )

    def test_color_pipeline_draft_only_profile_promotes_single_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = self._make_baseline(root)
            working_root = root / "working_states"
            runtime_cmd = root / "runtime" / "fractal_ui.cmd"
            runtime_cmd.parent.mkdir(parents=True, exist_ok=True)
            runtime_cmd.write_text("@echo off\n", encoding="utf-8")

            def fake_replay(runtime_cmd_path: Path, candidate_path: Path, replay_dir: Path, timeout_seconds: float = 90.0) -> ProcessResult:
                replay_dir.mkdir(parents=True, exist_ok=True)
                replay_doc = (
                    candidate_path.read_text(encoding="utf-8")[:-2]
                    + ', "color_pipeline_draft": {"lanes": [{"lane_id": "shape", "function_id": "repeat"}]}, "sidecar_orientation": {"yaw": 0.1}}\n'
                )
                (replay_dir / "state.json").write_text(replay_doc, encoding="utf-8")
                (replay_dir / "frame.bmp").write_text("bmp", encoding="utf-8")
                return ProcessResult(
                    command=["cmd.exe"],
                    cwd=str(runtime_cmd_path.parent),
                    pid=123,
                    exit_code=0,
                    timed_out=False,
                    elapsed_seconds=0.1,
                    stdout="ok",
                    stderr="",
                    observed_process_tree=[],
                )

            with patch("cuda_fractal_state_tool.state_workflow.replay_transport_candidate", side_effect=fake_replay), patch(
                "cuda_fractal_state_tool.state_workflow.build_runtime_identity",
                return_value={"launcher_sha256": "abc"},
            ):
                baseline_sha = sha256_file(manifest_path.with_name("state.json"))
                result = execute_proposal_workflow(
                    build_noop_example(baseline_sha),
                    manifest_path,
                    working_root,
                    "promoted_draft_only_run",
                    runtime_cmd_path=runtime_cmd,
                    promotion_profile="color_pipeline_draft_only_v1",
                )

            promoted_text = result.promoted_state_path.read_text(encoding="utf-8")
            report_text = result.promotion_report_path.read_text(encoding="utf-8")
            self.assertIn('"color_pipeline_draft"', promoted_text)
            self.assertNotIn('"sidecar_orientation"', promoted_text)
            self.assertIn('"allowed_keys": [', report_text)
            self.assertIn('"color_pipeline_draft"', report_text)
            self.assertNotIn('"sidecar_orientation"', report_text)

    def test_sidecar_orientation_only_profile_promotes_single_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = self._make_baseline(root)
            working_root = root / "working_states"
            runtime_cmd = root / "runtime" / "fractal_ui.cmd"
            runtime_cmd.parent.mkdir(parents=True, exist_ok=True)
            runtime_cmd.write_text("@echo off\n", encoding="utf-8")

            def fake_replay(runtime_cmd_path: Path, candidate_path: Path, replay_dir: Path, timeout_seconds: float = 90.0) -> ProcessResult:
                replay_dir.mkdir(parents=True, exist_ok=True)
                replay_doc = (
                    candidate_path.read_text(encoding="utf-8")[:-2]
                    + ', "color_pipeline_draft": {"lanes": [{"lane_id": "shape", "function_id": "repeat"}]}, "sidecar_orientation": {"yaw": 0.1}}\n'
                )
                (replay_dir / "state.json").write_text(replay_doc, encoding="utf-8")
                (replay_dir / "frame.bmp").write_text("bmp", encoding="utf-8")
                return ProcessResult(
                    command=["cmd.exe"],
                    cwd=str(runtime_cmd_path.parent),
                    pid=123,
                    exit_code=0,
                    timed_out=False,
                    elapsed_seconds=0.1,
                    stdout="ok",
                    stderr="",
                    observed_process_tree=[],
                )

            with patch("cuda_fractal_state_tool.state_workflow.replay_transport_candidate", side_effect=fake_replay), patch(
                "cuda_fractal_state_tool.state_workflow.build_runtime_identity",
                return_value={"launcher_sha256": "abc"},
            ):
                baseline_sha = sha256_file(manifest_path.with_name("state.json"))
                result = execute_proposal_workflow(
                    build_noop_example(baseline_sha),
                    manifest_path,
                    working_root,
                    "promoted_sidecar_only_run",
                    runtime_cmd_path=runtime_cmd,
                    promotion_profile="sidecar_orientation_only_v1",
                )

            promoted_text = result.promoted_state_path.read_text(encoding="utf-8")
            report_text = result.promotion_report_path.read_text(encoding="utf-8")
            self.assertIn('"sidecar_orientation"', promoted_text)
            self.assertNotIn('"color_pipeline_draft"', promoted_text)
            self.assertIn('"allowed_keys": [', report_text)
            self.assertIn('"sidecar_orientation"', report_text)
            self.assertNotIn('"color_pipeline_draft"', report_text)


if __name__ == "__main__":
    unittest.main()
