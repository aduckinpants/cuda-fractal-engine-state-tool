from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.json_utils import dumps_pretty
from cuda_fractal_state_tool.process_utils import ProcessResult
from cuda_fractal_state_tool.proposal_cli import main as proposal_main
from cuda_fractal_state_tool.runtime_surface import sha256_file
from cuda_fractal_state_tool.validation_runs import main as validation_runs_main
from cuda_fractal_state_tool.workflow_cli import main as workflow_main


class Phase3DraftSmokeCliTests(unittest.TestCase):
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

    def test_cli_draft_smoke_proposal_to_workflow_to_validation_query(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = self._make_baseline(root)
            working_root = root / "working_states"
            proposal_path = root / "proposal_draft.json"
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

            proposal_exit = proposal_main(
                [
                    "--example",
                    "color-pipeline-draft",
                    "--draft-lane",
                    "shape",
                    "--draft-function",
                    "identity",
                    "--baseline-manifest",
                    str(manifest_path),
                    "--out",
                    str(proposal_path),
                ]
            )
            self.assertEqual(proposal_exit, 0)
            self.assertTrue(proposal_path.exists())

            with patch("cuda_fractal_state_tool.state_workflow.build_runtime_identity", return_value=identity), patch(
                "cuda_fractal_state_tool.state_workflow.run_command",
                side_effect=fake_run_command,
            ), patch("cuda_fractal_state_tool.state_workflow.replay_transport_candidate", side_effect=fake_replay):
                workflow_stdout = io.StringIO()
                with redirect_stdout(workflow_stdout):
                    workflow_exit = workflow_main(
                        [
                            "--proposal",
                            str(proposal_path),
                            "--baseline-manifest",
                            str(manifest_path),
                            "--working-root",
                            str(working_root),
                            "--state-id",
                            "draft_smoke",
                            "--runtime-cmd",
                            str(runtime_cmd),
                            "--promotion-profile",
                            "color_pipeline_draft_only_v1",
                        ]
                    )

            self.assertEqual(workflow_exit, 0)
            workflow_payload = json.loads(workflow_stdout.getvalue())
            self.assertEqual(workflow_payload["status"], "runtime_proof_succeeded")
            self.assertIsNotNone(workflow_payload["validation_runs_index_path"])

            index_path = Path(workflow_payload["validation_runs_index_path"])
            validation_stdout = io.StringIO()
            with redirect_stdout(validation_stdout):
                query_exit = validation_runs_main(
                    [
                        "--index",
                        str(index_path),
                        "--list",
                        "--promotion-profile",
                        "color_pipeline_draft_only_v1",
                    ]
                )

            self.assertEqual(query_exit, 0)
            listed_runs = json.loads(validation_stdout.getvalue())
            self.assertEqual(len(listed_runs), 1)
            self.assertEqual(listed_runs[0]["run_id"], "draft_smoke")
            self.assertTrue(listed_runs[0]["draft_override_present"])
            self.assertEqual(listed_runs[0]["draft_lane_count"], 1)


if __name__ == "__main__":
    unittest.main()
