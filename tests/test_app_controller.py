from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.app import Phase1Controller, Phase1Paths
from cuda_fractal_state_tool.json_utils import dumps_pretty
from cuda_fractal_state_tool.state_workflow import WorkflowResult
from cuda_fractal_state_tool.proposal import parse_proposal_v1


class AppControllerTests(unittest.TestCase):
    def _make_probe_root(self, root: Path) -> Path:
        probe = root / "runtime_probe"
        (probe / "capture_one").mkdir(parents=True)
        (probe / "replay_one").mkdir(parents=True)
        state_text = '{"state_version": 3, "fractal_type": "explaino_all", "view": {}, "params": {"max_iter": 500, "color_shape": "identity", "color_signal": "root_index", "color_palette": "joy", "color_grading": "basin_default"}, "render": {}}\n'
        (probe / "capture_one" / "state.json").write_text(state_text, encoding="utf-8")
        (probe / "replay_one" / "state.json").write_text('{"state_version": 3, "fractal_type": "explaino_all", "view": {}, "params": {"max_iter": 500, "color_shape": "identity", "color_signal": "root_index", "color_palette": "joy", "color_grading": "basin_default"}, "render": {}, "color_pipeline_draft": {"lanes": []}}\n', encoding="utf-8")
        (probe / "runtime_identity.json").write_text(dumps_pretty({"launcher_sha256": "abc", "runtime_schema_sha256": "one", "source_schema_sha256": "two", "resolved_executable_sha256": "xyz"}), encoding="utf-8")
        (probe / "summary.json").write_text(dumps_pretty({"replay_one_state_exists": True}), encoding="utf-8")
        return probe

    def test_controller_bootstraps_baseline_and_examples(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            probe = self._make_probe_root(root)
            paths = Phase1Paths(
                root,
                probe,
                root / "baselines",
                root / "baselines" / "runtime-default-v1" / "manifest.json",
                root / "working_states",
                root / "validation_runs",
            )
            controller = Phase1Controller(paths, runtime_cmd_path=Path(r"D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd"))
            self.assertIn("runtime-default-v1", controller.baseline_status_text())
            self.assertIn('"overrides": {}', controller.example_noop_proposal())
            self.assertIn('"params.color_shape": "repeat"', controller.example_color_proposal())
            self.assertIn('"params.color_grading": "basin_default"', controller.example_grading_proposal())
            self.assertIn('"params.color_signal": "iteration_count"', controller.example_color_triplet_proposal())
            packet = controller.intake_packet()
            self.assertIn("params.color_shape", packet)
            self.assertIn("params.color_signal", packet)
            self.assertIn("params.color_palette", packet)
            self.assertIn("params.color_grading", packet)
            self.assertIn("schema provenance status: mismatched", packet)

            output_groups = controller.output_folder_groups("demo_state")
            self.assertIn("capture_finding_output_folder", output_groups)
            self.assertIn("next_working_state_subfolder", output_groups)
            self.assertIn("next_validation_run_subfolder", output_groups)
            self.assertTrue(output_groups["next_working_state_subfolder"].endswith("demo_state"))

            proposal_from_capture = controller.proposal_from_state_json_path(probe / "capture_one" / "state.json")
            parsed = parse_proposal_v1(
                proposal_from_capture,
                controller.baseline.baseline_id,
                controller.baseline.manifest["state_sha256"],
            )
            self.assertEqual(dict(parsed.overrides), {})

            mutated_state_path = probe / "capture_mutated.json"
            mutated_state_path.write_text(
                '{"state_version": 3, "fractal_type": "explaino_all", "view": {}, "params": {"max_iter": 700, "color_shape": "identity", "color_signal": "root_index", "color_palette": "joy", "color_grading": "basin_default"}, "render": {}}\n',
                encoding="utf-8",
            )
            proposal_from_mutated = controller.proposal_from_state_json_path(mutated_state_path)
            parsed_mutated = parse_proposal_v1(
                proposal_from_mutated,
                controller.baseline.baseline_id,
                controller.baseline.manifest["state_sha256"],
            )
            self.assertEqual(parsed_mutated.overrides["params.max_iter"], 700)

    def test_replay_prove_forwards_selected_promotion_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            probe = self._make_probe_root(root)
            paths = Phase1Paths(
                root,
                probe,
                root / "baselines",
                root / "baselines" / "runtime-default-v1" / "manifest.json",
                root / "working_states",
                root / "validation_runs",
            )
            controller = Phase1Controller(paths, runtime_cmd_path=Path(r"D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd"))

            result = WorkflowResult(
                status="runtime_proof_succeeded",
                working_state_dir=root / "working_states" / "run",
                validation_run_dir=root / "validation_runs" / "run",
                validation_run_manifest_path=root / "validation_runs" / "run" / "manifest.json",
                validation_runs_index_path=root / "validation_runs" / "index.json",
                runtime_status="runtime_success",
                promotion_profile="color_pipeline_draft_only_v1",
                promoted_state_path=root / "working_states" / "run" / "promoted_state.json",
                promotion_report_path=root / "working_states" / "run" / "promotion_report.json",
                transport_candidate_path=root / "working_states" / "run" / "transport_candidate.json",
                proven_state_path=root / "working_states" / "run" / "state.json",
                replay_state_path=root / "working_states" / "run" / "replay" / "state.json",
                diff=None,
                validation_path=root / "working_states" / "run" / "validation.json",
            )

            with patch("cuda_fractal_state_tool.app.execute_proposal_workflow", return_value=result) as mock_execute:
                controller.replay_prove(controller.example_noop_proposal(), promotion_profile="color_pipeline_draft_only_v1")

            self.assertEqual(controller.available_promotion_profiles()[0], "none")
            self.assertEqual(mock_execute.call_args.kwargs["promotion_profile"], "color_pipeline_draft_only_v1")

    def test_imported_finding_workflow_methods(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            probe = self._make_probe_root(root)
            paths = Phase1Paths(
                root,
                probe,
                root / "baselines",
                root / "baselines" / "runtime-default-v1" / "manifest.json",
                root / "working_states",
                root / "validation_runs",
            )
            controller = Phase1Controller(paths, runtime_cmd_path=Path(r"D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd"))

            workspace_root = root / "findings_workspace"
            imported = controller.import_finding(probe / "capture_one", workspace_root)
            self.assertTrue(imported.finding_id)
            self.assertIn(imported.finding_id, controller.imported_finding_status_text())

            proposal_text = controller.example_imported_finding_noop_proposal()
            parsed = parse_proposal_v1(proposal_text, imported.finding_id, imported.authoring_base_state_sha256)
            self.assertEqual(parsed.base_state_id, imported.finding_id)

    def test_replay_prove_imported_finding_uses_shared_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            probe = self._make_probe_root(root)
            paths = Phase1Paths(
                root,
                probe,
                root / "baselines",
                root / "baselines" / "runtime-default-v1" / "manifest.json",
                root / "working_states",
                root / "validation_runs",
            )
            controller = Phase1Controller(paths, runtime_cmd_path=Path(r"D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd"))

            workspace_root = root / "findings_workspace"
            imported = controller.import_finding(probe / "capture_one", workspace_root)
            proposal_text = controller.example_imported_finding_noop_proposal()

            result = WorkflowResult(
                status="runtime_proof_succeeded",
                working_state_dir=root / "ws" / "run",
                validation_run_dir=root / "ws" / "run" / "validation",
                validation_run_manifest_path=root / "ws" / "run" / "validation" / "manifest.json",
                validation_runs_index_path=root / "ws" / "run" / "validation" / "index.json",
                runtime_status="runtime_success",
                promotion_profile="none",
                promoted_state_path=None,
                promotion_report_path=None,
                transport_candidate_path=root / "ws" / "run" / "transport_candidate.json",
                proven_state_path=root / "ws" / "run" / "state.json",
                replay_state_path=root / "ws" / "run" / "replay" / "state.json",
                diff=None,
                validation_path=root / "ws" / "run" / "validation.json",
            )

            with patch("cuda_fractal_state_tool.app.execute_imported_finding_workflow", return_value=result) as mock_execute:
                received = controller.replay_prove_imported_finding(
                    source_capture_path=probe / "capture_one",
                    workspace_root=workspace_root,
                    proposal_text=proposal_text,
                    promotion_profile="none",
                )

            self.assertEqual(received.status, "runtime_proof_succeeded")
            self.assertEqual(controller.last_workflow_result, result)
            self.assertEqual(mock_execute.call_args.kwargs["workspace_root"], workspace_root)
            self.assertEqual(mock_execute.call_args.kwargs["source_capture_path"], probe / "capture_one")
            self.assertIn(imported.finding_id, proposal_text)

    def test_imported_finding_intake_packet_is_actionable_and_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            probe = self._make_probe_root(root)
            paths = Phase1Paths(
                root,
                probe,
                root / "baselines",
                root / "baselines" / "runtime-default-v1" / "manifest.json",
                root / "working_states",
                root / "validation_runs",
            )
            controller = Phase1Controller(paths, runtime_cmd_path=Path(r"D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd"))
            imported = controller.import_finding(probe / "capture_one", root / "findings_workspace")

            packet = controller.imported_finding_intake_packet()

            self.assertIn("Return JSON only.", packet)
            self.assertIn(f'"finding_id": "{imported.finding_id}"', packet)
            self.assertIn(f'"sha256": "{imported.authoring_base_state_sha256}"', packet)
            self.assertIn("Allowed override paths (bounded)", packet)
            self.assertIn("- params.max_iter", packet)
            self.assertIn("- Do not output unknown override paths.", packet)


if __name__ == "__main__":
    unittest.main()