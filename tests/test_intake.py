from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.intake import build_intake_packet
from cuda_fractal_state_tool.json_utils import dumps_pretty
from cuda_fractal_state_tool.runtime_surface import sha256_file


class IntakeTests(unittest.TestCase):
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
                    "runtime_identity": {
                        "launcher_sha256": "abc",
                        "resolved_executable_sha256": "def",
                        "runtime_schema_sha256": "one",
                        "source_schema_sha256": "two",
                    },
                    "replay_proven": True,
                }
            ),
            encoding="utf-8",
        )
        return manifest_path

    def test_intake_packet_includes_color_triplet_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = self._make_baseline(root)
            replay_path = root / "replay_state.json"
            replay_path.write_text(
                '{"state_version": 3, "fractal_type": "explaino_all", "view": {}, "params": {"max_iter": 500, "color_shape": "identity", "color_signal": "root_index", "color_palette": "joy", "color_grading": "basin_default"}, "render": {}, "color_pipeline_draft": {"lanes": [{"lane_id": "shape", "function_id": "identity"}]}}\n',
                encoding="utf-8",
            )

            packet = build_intake_packet(manifest_path, replay_path)
            self.assertIn("6. Metadata authority chain expectations", packet)
            self.assertIn("deployed compiled UI-Salt contract", packet)
            self.assertIn("8. Color triplet contract", packet)
            self.assertIn("Color triplet coupling rule", packet)
            self.assertIn("- root_index + joy + basin_default", packet)
            self.assertIn("9. Exact finding packet requirement", packet)
            self.assertIn("baseline packet does not authorize color_pipeline_draft", packet)
            self.assertIn("11. Proposal envelope", packet)


if __name__ == "__main__":
    unittest.main()
