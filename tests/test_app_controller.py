from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.app import Phase1Controller, Phase1Paths
from cuda_fractal_state_tool.json_utils import dumps_pretty


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
            paths = Phase1Paths(root, probe, root / "baselines", root / "baselines" / "runtime-default-v1" / "manifest.json", root / "working_states")
            controller = Phase1Controller(paths, runtime_cmd_path=Path(r"D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd"))
            self.assertIn("runtime-default-v1", controller.baseline_status_text())
            self.assertIn('"overrides": {}', controller.example_noop_proposal())
            self.assertIn('"params.color_shape": "repeat"', controller.example_color_proposal())
            self.assertIn('"params.color_grading": "basin_default"', controller.example_grading_proposal())
            packet = controller.intake_packet()
            self.assertIn("params.color_shape", packet)
            self.assertIn("params.color_grading", packet)
            self.assertIn("schema provenance status: mismatched", packet)


if __name__ == "__main__":
    unittest.main()