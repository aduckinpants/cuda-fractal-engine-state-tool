from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.baseline import BASELINE_ID, freeze_phase0_baseline, load_frozen_baseline
from cuda_fractal_state_tool.json_utils import dumps_pretty


class BaselineTests(unittest.TestCase):
    def _make_probe_root(self, root: Path) -> Path:
        probe = root / "runtime_probe"
        (probe / "capture_one").mkdir(parents=True)
        (probe / "replay_one").mkdir(parents=True)
        (probe / "capture_one" / "state.json").write_text('{"state_version": 3, "fractal_type": "newton", "view": {}, "params": {}, "render": {}}\n', encoding="utf-8")
        (probe / "replay_one" / "state.json").write_text('{"state_version": 3, "fractal_type": "newton", "view": {}, "params": {}, "render": {}}\n', encoding="utf-8")
        (probe / "runtime_identity.json").write_text(dumps_pretty({"launcher_sha256": "abc"}), encoding="utf-8")
        (probe / "summary.json").write_text(dumps_pretty({"replay_one_state_exists": True}), encoding="utf-8")
        return probe

    def test_freeze_baseline_creates_manifest_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            probe = self._make_probe_root(root)
            frozen = freeze_phase0_baseline(probe, root / "baselines")
            self.assertEqual(frozen.baseline_id, BASELINE_ID)
            self.assertTrue(frozen.state_path.exists())
            self.assertTrue(frozen.manifest_path.exists())
            loaded = load_frozen_baseline(frozen.manifest_path)
            self.assertEqual(loaded.baseline_id, BASELINE_ID)

    def test_freeze_baseline_requires_replay_proven_phase0_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            probe = self._make_probe_root(root)
            (probe / "summary.json").write_text(dumps_pretty({"replay_one_state_exists": False}), encoding="utf-8")
            with self.assertRaises(ValueError):
                freeze_phase0_baseline(probe, root / "baselines")


if __name__ == "__main__":
    unittest.main()
