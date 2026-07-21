from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.finding_workflow import execute_imported_finding_workflow
from cuda_fractal_state_tool.state_workflow import WorkflowResult


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class FindingWorkflowTests(unittest.TestCase):
    def test_proposal_base_must_match_imported_finding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            capture_root = Path(temp_dir) / "capture"
            _write_json(capture_root / "state.json", {"state_version": 3, "params": {"max_iter": 500}})

            proposal = json.dumps(
                {
                    "proposal_version": 1,
                    "base_state": {"finding_id": "wrong", "sha256": "wrong"},
                    "overrides": {},
                }
            )

            with self.assertRaises(ValueError):
                execute_imported_finding_workflow(
                    capture_root,
                    proposal,
                    workspace_root,
                    runtime_cmd_path=Path("C:/runtime/fractal_ui.cmd"),
                )

    def test_repeated_runs_get_unique_state_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            capture_root = Path(temp_dir) / "capture"
            _write_json(capture_root / "state.json", {"state_version": 3, "params": {"max_iter": 500}})

            captured_state_ids: list[str] = []

            def _fake_execute_proposal_workflow(**kwargs):
                captured_state_ids.append(kwargs["state_id"])
                state_dir = kwargs["working_states_root"] / kwargs["state_id"]
                return WorkflowResult(
                    status="runtime_proof_succeeded",
                    working_state_dir=state_dir,
                    validation_run_dir=state_dir,
                    validation_run_manifest_path=state_dir / "manifest.json",
                    validation_runs_index_path=state_dir / "index.json",
                    runtime_status="runtime_success",
                    promotion_profile="none",
                    promoted_state_path=None,
                    promotion_report_path=None,
                    transport_candidate_path=state_dir / "transport_candidate.json",
                    proven_state_path=state_dir / "state.json",
                    replay_state_path=state_dir / "replay" / "state.json",
                    diff=None,
                    validation_path=state_dir / "validation.json",
                )

            with patch("cuda_fractal_state_tool.finding_workflow.execute_proposal_workflow", side_effect=_fake_execute_proposal_workflow):
                # Discover finding id and base hash from first import.
                from cuda_fractal_state_tool.finding_workspace import SourceCaptureImporter

                importer = SourceCaptureImporter(workspace_root)
                imported = importer.import_capture(capture_root)
                proposal = json.dumps(
                    {
                        "proposal_version": 1,
                        "base_state": {"finding_id": imported.finding_id, "sha256": imported.authoring_base_state_sha256},
                        "overrides": {},
                    }
                )

                execute_imported_finding_workflow(capture_root, proposal, workspace_root)
                execute_imported_finding_workflow(capture_root, proposal, workspace_root)

            self.assertEqual(len(captured_state_ids), 2)
            self.assertNotEqual(captured_state_ids[0], captured_state_ids[1])


if __name__ == "__main__":
    unittest.main()