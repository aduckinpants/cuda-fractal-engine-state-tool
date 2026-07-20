from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.json_utils import dumps_pretty
from cuda_fractal_state_tool.proposal import build_noop_example
from cuda_fractal_state_tool.runtime_surface import sha256_file
from cuda_fractal_state_tool.state_workflow import execute_proposal_workflow
from cuda_fractal_state_tool.process_utils import ProcessResult


class StateWorkflowIndexTests(unittest.TestCase):
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

    def test_validation_runs_index_tracks_multiple_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = self._make_baseline(root)
            working_root = root / "working_states"
            runtime_cmd = root / "runtime" / "fractal_ui.cmd"
            runtime_cmd.parent.mkdir(parents=True, exist_ok=True)
            runtime_cmd.write_text("@echo off\n", encoding="utf-8")

            def fake_replay(runtime_cmd_path: Path, candidate_path: Path, replay_dir: Path, timeout_seconds: float = 90.0) -> ProcessResult:
                replay_dir.mkdir(parents=True, exist_ok=True)
                (replay_dir / "state.json").write_text(candidate_path.read_text(encoding="utf-8"), encoding="utf-8")
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
                first = execute_proposal_workflow(
                    build_noop_example(baseline_sha),
                    manifest_path,
                    working_root,
                    "run_one",
                    runtime_cmd_path=runtime_cmd,
                )
                second = execute_proposal_workflow(
                    build_noop_example(baseline_sha),
                    manifest_path,
                    working_root,
                    "run_two",
                    runtime_cmd_path=runtime_cmd,
                )

            self.assertTrue(first.validation_runs_index_path.exists())
            index_text = first.validation_runs_index_path.read_text(encoding="utf-8")
            self.assertIn('"run_id": "run_one"', index_text)
            self.assertIn('"run_id": "run_two"', index_text)
            self.assertIn('"runtime_status": "runtime_success"', index_text)
            index_obj = json.loads(index_text)
            manifest_paths = [entry["manifest_path"] for entry in index_obj["entries"]]
            self.assertIn(str(first.validation_run_manifest_path.resolve()), manifest_paths)
            self.assertIn(str(second.validation_run_manifest_path.resolve()), manifest_paths)


if __name__ == "__main__":
    unittest.main()
