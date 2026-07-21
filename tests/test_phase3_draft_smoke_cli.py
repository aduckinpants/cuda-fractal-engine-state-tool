from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.json_utils import dumps_pretty
from cuda_fractal_state_tool.process_utils import ProcessResult
from cuda_fractal_state_tool.proposal_cli import main as proposal_main
from cuda_fractal_state_tool.runtime_surface import sha256_file
from cuda_fractal_state_tool.workflow_cli import main as workflow_main


class Phase3DraftSmokeCliTests(unittest.TestCase):
    def test_archived_direct_draft_smoke_now_fails_closed_before_replay(self) -> None:
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
            proposal_path = root / "proposal.json"
            self.assertEqual(
                proposal_main(
                    [
                        "--example",
                        "color-pipeline-draft",
                        "--draft-lane",
                        "shape",
                        "--draft-function",
                        "repeat",
                        "--baseline-manifest",
                        str(manifest_path),
                        "--out",
                        str(proposal_path),
                    ]
                ),
                0,
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

            with patch("cuda_fractal_state_tool.state_workflow.build_runtime_identity", return_value=identity), patch(
                "cuda_fractal_state_tool.state_workflow.run_command", side_effect=fake_run
            ), patch("cuda_fractal_state_tool.state_workflow.replay_transport_candidate") as replay:
                with self.assertRaisesRegex(ValueError, "requires_engine_action_workflow"):
                    workflow_main(
                        [
                            "--proposal",
                            str(proposal_path),
                            "--baseline-manifest",
                            str(manifest_path),
                            "--working-root",
                            str(root / "working_states"),
                            "--runtime-cmd",
                            str(runtime_cmd),
                        ]
                    )
            replay.assert_not_called()


if __name__ == "__main__":
    unittest.main()
