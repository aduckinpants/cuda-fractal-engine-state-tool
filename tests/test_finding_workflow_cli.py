from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.finding_workflow_cli import main
from cuda_fractal_state_tool.state_workflow import WorkflowResult


class FindingWorkflowCliTests(unittest.TestCase):
    def _result(self, root: Path, status: str) -> WorkflowResult:
        run_dir = root / "run"
        return WorkflowResult(
            status=status,
            working_state_dir=run_dir,
            validation_run_dir=run_dir / "validation",
            validation_run_manifest_path=run_dir / "validation" / "manifest.json",
            validation_runs_index_path=run_dir / "validation" / "index.json",
            runtime_status="runtime_success" if status == "runtime_proof_succeeded" else "runtime_failure",
            promotion_profile="none",
            promoted_state_path=None,
            promotion_report_path=None,
            transport_candidate_path=run_dir / "transport_candidate.json",
            proven_state_path=run_dir / "state.json" if status == "runtime_proof_succeeded" else None,
            replay_state_path=run_dir / "replay" / "state.json" if status == "runtime_proof_succeeded" else None,
            diff=None,
            validation_path=run_dir / "validation.json",
        )

    def test_cli_emits_json_and_success_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path = root / "proposal.json"
            proposal_path.write_text('{"proposal_version":1,"base_state":{"finding_id":"fid","sha256":"sha"},"overrides":{}}', encoding="utf-8")

            with patch(
                "cuda_fractal_state_tool.finding_workflow_cli.execute_imported_finding_workflow",
                return_value=self._result(root, "runtime_proof_succeeded"),
            ):
                out = io.StringIO()
                with redirect_stdout(out):
                    exit_code = main(
                        [
                            "--workspace-root",
                            str(root / "workspace"),
                            "--source-capture",
                            str(root / "capture"),
                            "--proposal",
                            str(proposal_path),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["status"], "runtime_proof_succeeded")
            self.assertIsNotNone(payload["proven_state_path"])

    def test_cli_returns_nonzero_when_proof_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_path = root / "proposal.json"
            proposal_path.write_text('{"proposal_version":1,"base_state":{"finding_id":"fid","sha256":"sha"},"overrides":{}}', encoding="utf-8")

            with patch(
                "cuda_fractal_state_tool.finding_workflow_cli.execute_imported_finding_workflow",
                return_value=self._result(root, "runtime_proof_failed"),
            ):
                out = io.StringIO()
                with redirect_stdout(out):
                    exit_code = main(
                        [
                            "--workspace-root",
                            str(root / "workspace"),
                            "--source-capture",
                            str(root / "capture"),
                            "--proposal",
                            str(proposal_path),
                        ]
                    )

            self.assertEqual(exit_code, 2)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["status"], "runtime_proof_failed")
            self.assertIsNone(payload["proven_state_path"])


if __name__ == "__main__":
    unittest.main()
