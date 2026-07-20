from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.workspace_layout import WorkspaceLayout


class WorkspaceLayoutTests(unittest.TestCase):
    def test_from_repo_root_builds_expected_generated_data_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            layout = WorkspaceLayout.from_repo_root(Path(temp_dir))

            self.assertEqual(layout.data_root, Path(temp_dir).resolve() / ".local")
            self.assertEqual(layout.runtime_probe_root, layout.data_root / "runtime_probe")
            self.assertEqual(layout.baselines_root, layout.data_root / "baselines")
            self.assertEqual(layout.cache_root, layout.data_root / "cache")
            self.assertEqual(layout.validation_runs_root, layout.data_root / "validation_runs")
            self.assertEqual(layout.working_states_root, layout.data_root / "working_states")
            self.assertEqual(layout.baseline_manifest_path("baseline-x"), layout.baselines_root / "baseline-x" / "manifest.json")
            self.assertEqual(layout.validation_run_dir("run-x"), layout.validation_runs_root / "run-x")


if __name__ == "__main__":
    unittest.main()