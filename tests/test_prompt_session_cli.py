from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.prompt_session_cli import main
from cuda_fractal_state_tool.state_workflow import WorkflowResult


class PromptSessionCliTests(unittest.TestCase):
    def _make_result(self, root: Path, state_id: str, status: str, runtime_status: str) -> WorkflowResult:
        run_dir = root / "working" / state_id
        validation_dir = root / "validation_runs" / state_id
        run_dir.mkdir(parents=True, exist_ok=True)
        validation_dir.mkdir(parents=True, exist_ok=True)
        validation_path = run_dir / "validation.json"
        validation_path.write_text("{}\n", encoding="utf-8")
        return WorkflowResult(
            status=status,
            working_state_dir=run_dir,
            validation_run_dir=validation_dir,
            validation_run_manifest_path=validation_dir / "manifest.json",
            validation_runs_index_path=validation_dir.parent / "index.json",
            runtime_status=runtime_status,
            promotion_profile="none",
            promoted_state_path=None,
            promotion_report_path=None,
            transport_candidate_path=run_dir / "transport_candidate.json",
            proven_state_path=(run_dir / "state.json") if status == "runtime_proof_succeeded" else None,
            replay_state_path=(run_dir / "replay" / "state.json") if status == "runtime_proof_succeeded" else None,
            diff=None,
            validation_path=validation_path,
        )

    def test_prompt_session_pack_runs_and_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_a = root / "proposal_a.json"
            proposal_b = root / "proposal_b.json"
            proposal_a.write_text('{"proposal_version":1,"base_state":{"id":"runtime-default-v1","sha256":"hash"},"overrides":{}}', encoding="utf-8")
            proposal_b.write_text('{"proposal_version":1,"base_state":{"id":"runtime-default-v1","sha256":"hash"},"overrides":{}}', encoding="utf-8")
            pack_path = root / "pack.json"
            pack_path.write_text(
                json.dumps(
                    {
                        "session_id": "smoke",
                        "cases": [
                            {
                                "case_id": "a",
                                "proposal_path": str(proposal_a),
                                "state_id": "run_a",
                                "expected_status": "runtime_proof_succeeded",
                                "expected_runtime_status": "runtime_success",
                            },
                            {
                                "case_id": "b",
                                "proposal_path": str(proposal_b),
                                "state_id": "run_b",
                                "expected_status": "runtime_proof_succeeded",
                                "expected_runtime_status": "runtime_success",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            baseline_manifest = root / "baselines" / "runtime-default-v1" / "manifest.json"
            baseline_manifest.parent.mkdir(parents=True, exist_ok=True)
            baseline_manifest.write_text("{}\n", encoding="utf-8")

            with patch(
                "cuda_fractal_state_tool.prompt_session_cli.execute_proposal_workflow",
                side_effect=[
                    self._make_result(root, "run_a", "runtime_proof_succeeded", "runtime_success"),
                    self._make_result(root, "run_b", "runtime_proof_succeeded", "runtime_success"),
                ],
            ):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "--pack",
                            str(pack_path),
                            "--baseline-manifest",
                            str(baseline_manifest),
                            "--working-root",
                            str(root / "working"),
                            "--runtime-cmd",
                            str(root / "runtime" / "fractal_ui.cmd"),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["case_count"], 2)

    def test_prompt_session_pack_fails_when_expectation_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal = root / "proposal.json"
            proposal.write_text('{"proposal_version":1,"base_state":{"id":"runtime-default-v1","sha256":"hash"},"overrides":{}}', encoding="utf-8")
            pack_path = root / "pack.json"
            pack_path.write_text(
                json.dumps(
                    {
                        "session_id": "smoke",
                        "cases": [
                            {
                                "case_id": "a",
                                "proposal_path": str(proposal),
                                "state_id": "run_a",
                                "expected_status": "runtime_proof_succeeded",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            baseline_manifest = root / "baselines" / "runtime-default-v1" / "manifest.json"
            baseline_manifest.parent.mkdir(parents=True, exist_ok=True)
            baseline_manifest.write_text("{}\n", encoding="utf-8")

            with patch(
                "cuda_fractal_state_tool.prompt_session_cli.execute_proposal_workflow",
                return_value=self._make_result(root, "run_a", "runtime_proof_failed", "runtime_failure"),
            ):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = main(
                        [
                            "--pack",
                            str(pack_path),
                            "--baseline-manifest",
                            str(baseline_manifest),
                            "--working-root",
                            str(root / "working"),
                            "--runtime-cmd",
                            str(root / "runtime" / "fractal_ui.cmd"),
                        ]
                    )

            self.assertEqual(exit_code, 2)
            payload = json.loads(stdout.getvalue())
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["cases"][0]["checks"][0]["ok"], False)


if __name__ == "__main__":
    unittest.main()
