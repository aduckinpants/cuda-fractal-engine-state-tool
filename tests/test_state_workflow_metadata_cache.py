from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.json_utils import dumps_pretty
from cuda_fractal_state_tool.process_utils import ProcessResult
from cuda_fractal_state_tool.proposal import build_noop_example
from cuda_fractal_state_tool.runtime_metadata_cache import runtime_identity_cache_key
from cuda_fractal_state_tool.runtime_surface import sha256_file
from cuda_fractal_state_tool.state_workflow import execute_proposal_workflow


class StateWorkflowMetadataCacheTests(unittest.TestCase):
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

    def _fake_replay(self, runtime_cmd_path: Path, candidate_path: Path, replay_dir: Path, timeout_seconds: float = 90.0) -> ProcessResult:
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

    def test_workflow_populates_metadata_cache_on_miss(self) -> None:
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
                    Path(command[-1]).write_text("{}\n", encoding="utf-8")
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

            with patch("cuda_fractal_state_tool.state_workflow.build_runtime_identity", return_value=identity), patch(
                "cuda_fractal_state_tool.state_workflow.run_command",
                side_effect=fake_run_command,
            ), patch("cuda_fractal_state_tool.state_workflow.replay_transport_candidate", side_effect=self._fake_replay):
                baseline_sha = sha256_file(manifest_path.with_name("state.json"))
                result = execute_proposal_workflow(
                    build_noop_example(baseline_sha),
                    manifest_path,
                    working_root,
                    "metadata_miss",
                    runtime_cmd_path=runtime_cmd,
                )

            cache_key = runtime_identity_cache_key(identity)
            cache_dir = root / "cache" / "runtime" / cache_key
            self.assertTrue((cache_dir / "describe-parameter-surface.json").exists())
            self.assertTrue((cache_dir / "describe-functions.json").exists())
            self.assertTrue((cache_dir / "runtime_identity.json").exists())

            validation = json.loads(result.validation_path.read_text(encoding="utf-8"))
            self.assertIn("runtime_metadata_cache", validation)
            self.assertFalse(validation["runtime_metadata_cache"]["cache_hit"])
            self.assertEqual(validation["runtime_metadata_cache"]["cache_key"], cache_key)

    def test_workflow_uses_metadata_cache_on_hit(self) -> None:
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
            cache_key = runtime_identity_cache_key(identity)
            cache_dir = root / "cache" / "runtime" / cache_key
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / "describe-parameter-surface.json").write_text("{}\n", encoding="utf-8")
            (cache_dir / "describe-functions.json").write_text("{}\n", encoding="utf-8")
            (cache_dir / "runtime_identity.json").write_text("{}\n", encoding="utf-8")

            def fail_run_command(*args, **kwargs):
                raise AssertionError("run_command should not run on metadata cache hit")

            with patch("cuda_fractal_state_tool.state_workflow.build_runtime_identity", return_value=identity), patch(
                "cuda_fractal_state_tool.state_workflow.run_command",
                side_effect=fail_run_command,
            ), patch("cuda_fractal_state_tool.state_workflow.replay_transport_candidate", side_effect=self._fake_replay):
                baseline_sha = sha256_file(manifest_path.with_name("state.json"))
                result = execute_proposal_workflow(
                    build_noop_example(baseline_sha),
                    manifest_path,
                    working_root,
                    "metadata_hit",
                    runtime_cmd_path=runtime_cmd,
                )

            validation = json.loads(result.validation_path.read_text(encoding="utf-8"))
            self.assertTrue(validation["runtime_metadata_cache"]["cache_hit"])
            self.assertEqual(validation["runtime_metadata_cache"]["cache_key"], cache_key)


if __name__ == "__main__":
    unittest.main()
