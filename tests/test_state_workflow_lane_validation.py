from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.json_utils import dumps_pretty
from cuda_fractal_state_tool.process_utils import ProcessResult
from cuda_fractal_state_tool.runtime_surface import sha256_file
from cuda_fractal_state_tool.state_workflow import execute_proposal_workflow


class StateWorkflowLaneValidationTests(unittest.TestCase):
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

    def test_workflow_rejects_unknown_lane_in_draft_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = self._make_baseline(root)
            working_root = root / "working_states"
            runtime_cmd = root / "runtime" / "fractal_ui.cmd"
            runtime_cmd.parent.mkdir(parents=True, exist_ok=True)
            runtime_cmd.write_text("@echo off\n", encoding="utf-8")

            identity = {
                "launcher_path": str(runtime_cmd.resolve()),
                "launcher_sha256": "launcher",
                "working_directory": str(runtime_cmd.parent.resolve()),
                "resolved_executable_path": None,
                "resolved_executable_sha256": None,
                "resolved_executable_file_version": None,
                "runtime_schema_path": None,
                "runtime_schema_sha256": None,
                "source_schema_path": None,
                "source_schema_sha256": None,
                "describe_parameter_surface_sha256": None,
                "describe_functions_sha256": None,
            }

            def fake_run_command(command, cwd, timeout_seconds=None, env=None):
                if "--describe-parameter-surface-json" in command:
                    Path(command[-1]).write_text("{}\n", encoding="utf-8")
                elif "--describe-functions-json" in command:
                    Path(command[-1]).write_text(
                        '{"lane_functions": [{"lane_id": "shape", "function_id": "identity"}]}\n',
                        encoding="utf-8",
                    )
                return ProcessResult(
                    command=list(command),
                    cwd=str(cwd),
                    pid=321,
                    exit_code=0,
                    timed_out=False,
                    elapsed_seconds=0.05,
                    stdout="ok",
                    stderr="",
                    observed_process_tree=[],
                )

            proposal_text = dumps_pretty(
                {
                    "proposal_version": 1,
                    "base_state": {
                        "id": "runtime-default-v1",
                        "sha256": sha256_file(manifest_path.with_name("state.json")),
                    },
                    "overrides": {
                        "color_pipeline_draft": {
                            "lanes": [
                                {
                                    "lane_id": "signal",
                                    "function_id": "root_index",
                                }
                            ]
                        }
                    },
                }
            )

            with patch("cuda_fractal_state_tool.state_workflow.build_runtime_identity", return_value=identity), patch(
                "cuda_fractal_state_tool.state_workflow.run_command",
                side_effect=fake_run_command,
            ), patch("cuda_fractal_state_tool.state_workflow.replay_transport_candidate") as mock_replay:
                with self.assertRaisesRegex(ValueError, "lane_unknown"):
                    execute_proposal_workflow(
                        proposal_text,
                        manifest_path,
                        working_root,
                        "lane_validation",
                        runtime_cmd_path=runtime_cmd,
                    )

            mock_replay.assert_not_called()


if __name__ == "__main__":
    unittest.main()
