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
    def test_legacy_direct_draft_workflow_fails_before_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            baseline_dir = root / "baselines" / "runtime-default-v1"
            baseline_dir.mkdir(parents=True)
            state_path = baseline_dir / "state.json"
            state_path.write_text(
                '{"state_version":3,"fractal_type":"explaino_all","view":{},"params":{"color_shape":"identity"},"render":{}}\n',
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
            runtime_cmd = root / "runtime" / "fractal_ui.cmd"
            runtime_cmd.parent.mkdir()
            runtime_cmd.write_text("@echo off\n", encoding="utf-8")
            identity = {
                "launcher_path": str(runtime_cmd),
                "launcher_sha256": "launcher",
                "working_directory": str(runtime_cmd.parent),
            }

            def fake_run(command, cwd, timeout_seconds=None, env=None):
                if "--describe-parameter-surface-json" in command:
                    Path(command[-1]).write_text("{}", encoding="utf-8")
                if "--describe-functions-json" in command:
                    Path(command[-1]).write_text('{"functions":[]}', encoding="utf-8")
                return ProcessResult(
                    command=list(command), cwd=str(cwd), pid=1, exit_code=0, timed_out=False,
                    elapsed_seconds=0.01, stdout="", stderr="", observed_process_tree=[]
                )

            proposal = dumps_pretty(
                {
                    "proposal_version": 1,
                    "base_state": {"id": "runtime-default-v1", "sha256": sha256_file(state_path)},
                    "overrides": {
                        "color_pipeline_draft": {
                            "lanes": [{"lane_id": "shape", "function_id": "repeat"}]
                        }
                    },
                }
            )
            with patch("cuda_fractal_state_tool.state_workflow.build_runtime_identity", return_value=identity), patch(
                "cuda_fractal_state_tool.state_workflow.run_command", side_effect=fake_run
            ), patch("cuda_fractal_state_tool.state_workflow.replay_transport_candidate") as replay:
                with self.assertRaisesRegex(ValueError, "requires_engine_action_workflow"):
                    execute_proposal_workflow(
                        proposal,
                        manifest_path,
                        root / "working_states",
                        "direct_draft",
                        runtime_cmd_path=runtime_cmd,
                    )
            replay.assert_not_called()


if __name__ == "__main__":
    unittest.main()
