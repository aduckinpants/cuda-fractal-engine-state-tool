from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.state_workflow import WorkflowResult
from cuda_fractal_state_tool.workflow_cli import main


class WorkflowCliTests(unittest.TestCase):
    def _make_result(self, root: Path, status: str) -> WorkflowResult:
        run_dir = root / "working" / "run"
        validation_dir = root / "validation_runs" / "run"
        return WorkflowResult(
            status=status,
            working_state_dir=run_dir,
            validation_run_dir=validation_dir,
            validation_run_manifest_path=validation_dir / "manifest.json",
            validation_runs_index_path=validation_dir.parent / "index.json",
            runtime_status="runtime_success" if status == "runtime_proof_succeeded" else "runtime_failure",
            promotion_profile="none",
            promoted_state_path=None,
            promotion_report_path=None,
            transport_candidate_path=run_dir / "transport_candidate.json",
            proven_state_path=(run_dir / "state.json") if status == "runtime_proof_succeeded" else None,
            replay_state_path=(run_dir / "replay" / "state.json") if status == "runtime_proof_succeeded" else None,
            diff=None,
            validation_path=run_dir / "validation.json",
        )

    def test_cli_emits_json_and_success_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path = root / "proposal.json"
            proposal_path.write_text('{"proposal_version":1,"base_state":{"id":"runtime-default-v1","sha256":"hash"},"overrides":{}}', encoding="utf-8")

            with patch("cuda_fractal_state_tool.workflow_cli.execute_proposal_workflow", return_value=self._make_result(root, "runtime_proof_succeeded")):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "--proposal",
                            str(proposal_path),
                            "--baseline-manifest",
                            str(root / "baselines" / "runtime-default-v1" / "manifest.json"),
                            "--working-root",
                            str(root / "working"),
                            "--state-id",
                            "manual_run",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "runtime_proof_succeeded")
            self.assertIsNotNone(payload["proven_state_path"])

    def test_cli_uses_nonzero_exit_code_for_failed_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path = root / "proposal.json"
            proposal_path.write_text('{"proposal_version":1,"base_state":{"id":"runtime-default-v1","sha256":"hash"},"overrides":{}}', encoding="utf-8")

            with patch("cuda_fractal_state_tool.workflow_cli.execute_proposal_workflow", return_value=self._make_result(root, "runtime_proof_failed")):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "--proposal",
                            str(proposal_path),
                            "--baseline-manifest",
                            str(root / "baselines" / "runtime-default-v1" / "manifest.json"),
                            "--working-root",
                            str(root / "working"),
                            "--state-id",
                            "manual_run",
                        ]
                    )

            self.assertEqual(exit_code, 2)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "runtime_proof_failed")
            self.assertIsNone(payload["proven_state_path"])

    def test_cli_launches_viewer_on_success_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path = root / "proposal.json"
            proposal_path.write_text('{"proposal_version":1,"base_state":{"id":"runtime-default-v1","sha256":"hash"},"overrides":{}}', encoding="utf-8")

            mock_popen = type("P", (), {"pid": 4242})()
            with patch("cuda_fractal_state_tool.workflow_cli.execute_proposal_workflow", return_value=self._make_result(root, "runtime_proof_succeeded")), patch(
                "cuda_fractal_state_tool.workflow_cli.launch_proven_candidate",
                return_value=mock_popen,
            ) as mock_launch:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "--proposal",
                            str(proposal_path),
                            "--baseline-manifest",
                            str(root / "baselines" / "runtime-default-v1" / "manifest.json"),
                            "--working-root",
                            str(root / "working"),
                            "--state-id",
                            "manual_run",
                            "--launch-viewer-on-success",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["launched_viewer_pid"], 4242)
            self.assertEqual(mock_launch.call_count, 1)

    def test_cli_does_not_launch_viewer_when_proof_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path = root / "proposal.json"
            proposal_path.write_text('{"proposal_version":1,"base_state":{"id":"runtime-default-v1","sha256":"hash"},"overrides":{}}', encoding="utf-8")

            with patch("cuda_fractal_state_tool.workflow_cli.execute_proposal_workflow", return_value=self._make_result(root, "runtime_proof_failed")), patch(
                "cuda_fractal_state_tool.workflow_cli.launch_proven_candidate"
            ) as mock_launch:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "--proposal",
                            str(proposal_path),
                            "--baseline-manifest",
                            str(root / "baselines" / "runtime-default-v1" / "manifest.json"),
                            "--working-root",
                            str(root / "working"),
                            "--state-id",
                            "manual_run",
                            "--launch-viewer-on-success",
                        ]
                    )

            self.assertEqual(exit_code, 2)
            payload = json.loads(stdout.getvalue())
            self.assertIsNone(payload["launched_viewer_pid"])
            mock_launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
